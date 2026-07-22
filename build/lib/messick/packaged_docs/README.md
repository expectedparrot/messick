# Messick

Validate that an LLM-agent study's results are credible before publishing. Three tiers: internal sanity checks (no `None` epidemic, sensible variance, no format failures), comparison against a benchmark dataset, and field validation against new human data. Use after running an LLM-agent study and before reporting findings.

## Why a validation framework

EDSL studies produce `Results` objects with arbitrarily many rows. The
fact that a run succeeded does not, on its own, tell you whether the
findings are credible. Three things have to be checked, in order, and
each is its own kind of evidence:

1. **Did the run technically work?** No mass-`None` answers, no
   stuck-on-one-option clusters, segments are populated, format
   compliance is acceptable. *Necessary but not sufficient.*
2. **Does the run agree with what we already know?** If similar
   questions have been asked of real humans, the LLM-agent
   distribution should look like the empirical one. *Necessary for
   any claim that the result generalizes.*
3. **Does the run predict out-of-sample behavior?** The strongest
   form of validation; rare in practice and study-specific. *Required
   for high-stakes deployment claims.*

Tier 1 is cheap and always required. Tier 2 is required for any
report that makes claims about real-world attitudes or behavior.
Tier 3 is bespoke.

## Installation

```bash
pip install -e /path/to/capabilities/packages/messick
```

## Tier 1 — Internal sanity

No external data needed. Run on any `Results` object.

```bash
messick validate tier1 --results data/results.json.gz --out analysis/validation/
```

What it checks per question:

| Check | Threshold | Severity |
|---|---|---|
| `None` rate | < 5% pass; 5–10% warn; > 10% fail | error if fail |
| Response diversity | ≥ 2 distinct answers across all rows | error if 1 |
| Modal-share dominance | top response < 95% | warn if higher |
| Cross-segment coverage | each agent trait combo has ≥ 1 response | warn if missing |

Plus run-level checks:

| Check | Description |
|---|---|
| Row count vs. expected | `len(results)` matches `S × A × M` (scenarios × agents × models) |
| Column-prefix completeness | All four prefixes present (`answer.*`, `scenario.*`, `agent.*`, `model.*`) |
| Repeated-sampling consistency | If `n > 1`, iteration counts are uniform per cell |

Outputs:

- `tier1_summary.md` — pass/fail with details.
- `tier1_per_question.csv` — per-question diagnostics.

## Tier 2 — Comparison validation

Needs a benchmark file: a JSON mapping question_name → list of
empirical proportions (in the same option order as the question).

```bash
messick validate tier2 \
    --results data/results.json.gz \
    --benchmark path/to/benchmark.json \
    --out analysis/validation/
```

What it computes:

- **Per-question TVD** — total variation distance between the LLM
  distribution and the benchmark.
- **Overall agreement** — mean TVD across benchmark questions.
- **Disagreement profile** — questions where TVD > 0.20 are flagged
  for review.

Interpretation:

| Mean TVD | Verdict |
|---|---|
| < 0.05 | Strong agreement |
| 0.05 – 0.10 | Substantial agreement |
| 0.10 – 0.20 | Moderate agreement; usable but caveat in report |
| > 0.20 | Substantial disagreement; investigate before publishing |

A high TVD doesn't automatically mean the LLM is wrong — sometimes
the benchmark is old, small-N, or non-representative. The
disagreement profile is the place to start that investigation.

Outputs:

- `tier2_summary.md` — overall result, recommendation.
- `tier2_comparison.csv` — per-question TVD.

## Tier 3 — Field validation

Outline only; bespoke per study. Typical pattern:

1. Use the calibrated agent panel to generate predictions for an
   *out-of-sample* question or condition.
2. Run the same question/condition with real humans (Prolific or
   another panel).
3. Compare aggregate metrics (mean / proportion / distribution).

Field validation is what justifies headline claims like "this
LLM-agent panel predicts real-world consumer behavior." It is not a
default step. Document the protocol fully in the report's Methods
section.

## What to write in the report

Whichever tiers ran, name them in Methods:

> Internal validation (Tier 1, Messick framework): all questions
> passed at < 5% `None` rate, with substantial response diversity
> across all agent segments.

> Comparison validation: the calibrated panel was compared against
> the [benchmark] data on [N] overlapping questions, with mean TVD
> = 0.07, indicating substantial agreement.

If any tier failed: name the failure, explain what was done. Hiding
failed validations is worse than not validating.

## Common pitfalls

- **Skipping Tier 1 because the run "looked fine."** Format-failure
  rates can be deceptively low *overall* while one specific question
  silently produces 40% `None`.
- **Treating Tier 2 disagreement as automatic LLM failure.**
  Investigate before concluding.
- **Cherry-picking Tier 2 questions.** Use the full benchmark.
- **Reporting only the tier that passed.** Document all tiers run,
  including failures. Selective reporting is a validity failure of
  its own kind.

## Cross-references

- `library:methods/response-validation.md` — conceptual reference.
- `library:methods/free-text-homogeneity.md` — separate diagnostic
  for free-text response quality (complements Tier 1).
- `recipe:run-with-llm-agents` — upstream run.
- `recipe:analyze-results` — downstream analysis (assumes validation
  passed).
- `recipe:write-report` — Methods section requirements.
- `recipe:manning` — calibration; itself produces validation outputs
  on a holdout question set.

## License

Same as the rest of the EP capabilities packages.
