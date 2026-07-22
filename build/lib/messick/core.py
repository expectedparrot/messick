#!/usr/bin/env python3
"""
validate_results.py — Internal validation checks for EDSL study results.

Runs automated checks on a Results file and reports issues:
  - Distribution plausibility: floor/ceiling effects, near-uniform responses
  - Response variance: answer columns with zero or near-zero variance
  - Known-group validity: configurable agent trait split with directional check

USAGE
-----
Copy this file into the study's analysis/ directory, then run from the study root:

    python analysis/validate_results.py
    python analysis/validate_results.py --results data/results.json.gz
    python analysis/validate_results.py --known-groups agent.political_leaning answer.policy_support

For multiple known-group comparisons, repeat the flag:

    python analysis/validate_results.py \\
        --known-groups agent.political_leaning answer.policy_support \\
        --known-groups agent.income_level answer.price_sensitivity

Exit codes:
  0  — no issues found
  1  — one or more issues found

NOTES
-----
This script checks what can be checked automatically. It cannot:
  - Verify that open-ended responses are meaningfully diverse (read a sample manually)
  - Confirm that known-group differences are in the *right* direction (you must judge that)
  - Replace a careful human review of the actual response content
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
CEILING_THRESHOLD   = 0.90   # flag if >90% of responses choose one option
FLOOR_THRESHOLD     = 0.90   # same check — modal option dominance
NEAR_ZERO_VARIANCE  = 0.01   # flag numeric columns with variance below this
MIN_GROUP_SIZE      = 3      # skip known-group check if either group has fewer than this


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass
class ValidationIssue:
    column: str
    severity: str          # "error" | "warning"
    check: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def add(self, column: str, severity: str, check: str, message: str) -> None:
        self.issues.append(ValidationIssue(column, severity, check, message))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_results(path: Path):
    """Load EDSL Results. Returns the Results object."""
    try:
        from edsl import Results
    except ImportError:
        print("ERROR: edsl is not installed. Run: pip install edsl")
        sys.exit(2)

    if not path.exists():
        print(f"ERROR: Results file not found: {path}")
        sys.exit(2)

    return Results.load(str(path))


def get_columns(results, prefix: str) -> list[str]:
    """Return all column names with a given prefix."""
    return [c for c in results.columns if c.startswith(prefix + ".")]


def get_values(results, column: str) -> list:
    """Extract a column as a flat list, skipping None/empty."""
    vals = results.select(column).to_list()
    return [v for v in vals if v is not None and v != ""]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_distribution_plausibility(results, report: ValidationReport) -> None:
    """
    For each multiple-choice answer column, flag if one option dominates (>90%).
    For numeric columns, flag extreme means (top or bottom 10% of observed range).
    """
    answer_cols = get_columns(results, "answer")

    for col in answer_cols:
        vals = get_values(results, col)
        if not vals:
            continue

        # Categorical: check modal dominance
        if isinstance(vals[0], str):
            from collections import Counter
            counts = Counter(vals)
            total = sum(counts.values())
            modal_frac = counts.most_common(1)[0][1] / total
            if modal_frac >= CEILING_THRESHOLD:
                report.add(
                    column=col,
                    severity="warning",
                    check="distribution",
                    message=(
                        f"{modal_frac*100:.0f}% of agents chose the same option "
                        f"('{counts.most_common(1)[0][0]}'). "
                        "This may indicate a ceiling/floor effect or a question that "
                        "doesn't discriminate across agents."
                    ),
                )

        # Numeric: check extreme mean
        elif isinstance(vals[0], (int, float)):
            try:
                numeric = [float(v) for v in vals]
                mn, mx = min(numeric), max(numeric)
                if mx == mn:
                    report.add(
                        column=col,
                        severity="warning",
                        check="variance",
                        message="All agents gave the same numeric response. No variance at all.",
                    )
                else:
                    mean = sum(numeric) / len(numeric)
                    pct = (mean - mn) / (mx - mn)
                    if pct >= 0.90:
                        report.add(
                            column=col,
                            severity="warning",
                            check="distribution",
                            message=(
                                f"Mean response ({mean:.2f}) is in the top 10% of the "
                                f"observed range ({mn}–{mx}). Possible ceiling effect."
                            ),
                        )
                    elif pct <= 0.10:
                        report.add(
                            column=col,
                            severity="warning",
                            check="distribution",
                            message=(
                                f"Mean response ({mean:.2f}) is in the bottom 10% of the "
                                f"observed range ({mn}–{mx}). Possible floor effect."
                            ),
                        )
            except (TypeError, ValueError):
                pass


def check_response_variance(results, report: ValidationReport) -> None:
    """
    Flag answer columns where all responses are identical (zero variance).
    Already caught partially by distribution check; this catches free-text uniformity.
    """
    answer_cols = get_columns(results, "answer")

    for col in answer_cols:
        vals = get_values(results, col)
        if not vals:
            continue
        if len(set(str(v) for v in vals)) == 1:
            report.add(
                column=col,
                severity="warning",
                check="variance",
                message=(
                    "Every agent gave the same response. The question may be too simple, "
                    "the persona conditioning may not be working, or the question text "
                    "implies a single correct answer."
                ),
            )


def check_known_groups(
    results,
    report: ValidationReport,
    trait_col: str,
    answer_col: str,
) -> None:
    """
    Compare mean numeric responses (or modal option) across two groups defined by
    trait_col. Reports the group means so the user can judge directionality manually.

    This check cannot determine whether the difference is in the *right* direction —
    only the researcher knows that. It confirms that a difference exists.
    """
    trait_vals = get_values(results, trait_col)
    answer_vals = get_values(results, answer_col)

    if len(trait_vals) != len(answer_vals):
        report.add(
            column=f"{trait_col} vs {answer_col}",
            severity="warning",
            check="known_groups",
            message="Column lengths differ — could not run known-group comparison.",
        )
        return

    # Group by unique trait values
    from collections import defaultdict
    groups: dict[str, list] = defaultdict(list)
    for trait, answer in zip(trait_vals, answer_vals):
        groups[str(trait)].append(answer)

    if len(groups) < 2:
        report.add(
            column=trait_col,
            severity="warning",
            check="known_groups",
            message=f"Only one unique value found in {trait_col} — cannot compare groups.",
        )
        return

    # Report group summaries
    summaries = []
    for group_name, answers in sorted(groups.items()):
        if len(answers) < MIN_GROUP_SIZE:
            summaries.append(f"  {group_name!r}: n={len(answers)} (too small to compare)")
            continue
        numeric = []
        for a in answers:
            try:
                numeric.append(float(a))
            except (TypeError, ValueError):
                pass

        if numeric:
            mean = sum(numeric) / len(numeric)
            summaries.append(f"  {group_name!r}: n={len(answers)}, mean={mean:.2f}")
        else:
            from collections import Counter
            modal = Counter(str(a) for a in answers).most_common(1)[0]
            summaries.append(
                f"  {group_name!r}: n={len(answers)}, "
                f"modal response='{modal[0]}' ({modal[1]/len(answers)*100:.0f}%)"
            )

    group_summary = "\n".join(summaries)

    # Check if all groups look identical (possible red flag)
    numeric_means = []
    for answers in groups.values():
        numeric = [float(a) for a in answers if _is_numeric(a)]
        if numeric:
            numeric_means.append(sum(numeric) / len(numeric))

    if len(numeric_means) >= 2:
        spread = max(numeric_means) - min(numeric_means)
        if spread < 0.1:
            report.add(
                column=f"{trait_col} vs {answer_col}",
                severity="warning",
                check="known_groups",
                message=(
                    f"Groups show almost no difference on {answer_col} "
                    f"(spread = {spread:.3f}). Check agent trait specificity and question wording.\n"
                    f"{group_summary}"
                ),
            )
            return

    # Groups differ — report for manual direction check
    report.add(
        column=f"{trait_col} vs {answer_col}",
        severity="info",
        check="known_groups",
        message=(
            f"Known-group comparison — verify the direction matches your expectation:\n"
            f"{group_summary}"
        ),
    )


def _is_numeric(val) -> bool:
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_validation(
    results_path: Path,
    known_groups: list[tuple[str, str]],
) -> ValidationReport:
    results = load_results(results_path)
    report = ValidationReport()

    check_distribution_plausibility(results, report)
    check_response_variance(results, report)

    for trait_col, answer_col in known_groups:
        check_known_groups(results, report, trait_col, answer_col)

    return report


def print_report(report: ValidationReport) -> int:
    """Print human-readable output. Returns exit code."""
    errors   = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity == "warning"]
    infos    = [i for i in report.issues if i.severity == "info"]

    if not report.issues:
        print("All checks passed. No issues found.")
        return 0

    for issue in errors + warnings + infos:
        marker = {"error": "ERROR  ", "warning": "WARN   ", "info": "INFO   "}[issue.severity]
        print(f"\n{marker}[{issue.check}] {issue.column}")
        print(f"  {issue.message}")

    print(
        f"\nResult: {len(errors)} error(s), {len(warnings)} warning(s), "
        f"{len(infos)} info(s)."
    )
    if infos:
        print(
            "INFO items require manual review — the script cannot determine "
            "whether group differences go in the right direction."
        )
    return 1 if (errors or warnings) else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Internal validation checks for EDSL study results."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("data/results.json.gz"),
        help="Path to Results file (default: data/results.json.gz)",
    )
    parser.add_argument(
        "--known-groups",
        nargs=2,
        metavar=("TRAIT_COL", "ANSWER_COL"),
        action="append",
        default=[],
        help=(
            "Known-group comparison: specify agent trait column and answer column. "
            "Example: --known-groups agent.political_leaning answer.policy_support. "
            "Repeat for multiple comparisons."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    results_path = args.results.resolve()
    known_groups = [(t, a) for t, a in args.known_groups]

    report = run_validation(results_path, known_groups)

    if args.json:
        import dataclasses
        print(json.dumps([dataclasses.asdict(i) for i in report.issues], indent=2))
        sys.exit(1 if report.has_errors else 0)
    else:
        sys.exit(print_report(report))


if __name__ == "__main__":
    main()
