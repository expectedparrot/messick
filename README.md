# messick — validation framework for LLM-agent study results
<!-- id: messick/messick -->

messick validates LLM-agent and EDSL study results through a three-tier framework: internal sanity checks, comparison against external or known benchmarks, and field validation against human data. The agent helps the user choose the validation tier, assemble evidence, run `messick validate`, and write validation claims that are proportional to the checks actually performed.

## When to use this
<!-- id: messick/when-to-use -->

- The user has synthetic-agent, survey, labeling, or simulation outputs and needs to know how much to trust them.
- Results will be reported to others and need transparent validity evidence.
- The study has assumptions that can be checked internally or compared to known benchmarks.
- The user needs a Methods/Limitations section grounded in validation, not just model confidence.

## When this is a stretch (and how to adapt)
<!-- id: messick/when-stretch -->

- The user has no external benchmark. Run Tier 1 internal sanity checks and clearly label the result as internally validated only.
- The user has a small human pilot. Use it as Tier 2 comparison evidence, and avoid claiming population validity.
- The synthetic study is still being designed. Use messick as a validation plan now, then run the checks after data exists.
- The output is qualitative. Pair messick with [bewley](#bewley/bewley) to compare themes and quote-level evidence rather than only numeric distributions.
- The user wants statistical proof that agents equal humans. Reframe to convergent evidence and discrepancy analysis; messick does not certify equivalence.

## Decision rule for the calling agent
<!-- id: messick/decision-rule -->

Before dispatching to messick, confirm:

1. There is an LLM-agent, EDSL, synthetic, or model-mediated result to validate.
2. The user needs validity evidence for interpretation or reporting.
3. At least one check can be run: internal consistency, comparison benchmark, or human/field reference.
4. The agent can distinguish findings from validation limitations in the final report.

If yes to the first three, messick is the right method.

## Inputs and elicitation
<!-- id: messick/inputs -->

### Study outputs
<!-- id: messick/inputs-study-outputs -->

What it is: the synthetic or model-mediated results to validate, such as EDSL result files, survey distributions, labels, transcripts, or simulation logs.

How the agent elicits this:
- Ask what was run, what files contain the outputs, and what the headline claim is.
- Ask whether the result is numeric, categorical, textual, behavioral, or multi-turn.
- Identify which parts of the output are central enough to validate.

Default to suggest: validate the smallest result table or transcript set that directly supports the user’s main claim.

Fallback: if outputs are messy, first produce a clean summary table or codebook using the originating package.

### Validation tier
<!-- id: messick/inputs-validation-tier -->

What it is: the level of evidence to assemble.

How the agent elicits this:
- Tier 1: internal sanity, invariants, missingness, impossible values, prompt adherence, distribution shape.
- Tier 2: comparison to published data, prior survey results, expert labels, or known benchmarks.
- Tier 3: field validation against human participants or real-world outcomes.
- Ask what evidence already exists and what is feasible within the task budget.

Default to suggest: run Tier 1 for every study; add Tier 2 whenever a benchmark is available.

Fallback: when only Tier 1 is possible, make limitations explicit and propose what Tier 2 or Tier 3 would require.

### Reporting claim
<!-- id: messick/inputs-reporting-claim -->

What it is: the level of confidence the user wants to state in a report.

How the agent elicits this:
- Ask what decision or claim the validation needs to support.
- Separate "the pipeline ran correctly" from "the synthetic population matches humans."
- Ask whether validation failures should block publication or become limitations.

Default to suggest: phrase conclusions as bounded evidence, e.g. "internally consistent and directionally aligned with benchmark X."

Fallback: if validation is weak, report results as exploratory and list concrete next validation steps.

## Outputs
<!-- id: messick/outputs -->

messick produces validation artifacts suitable for report inclusion:

- A structured validation result from `messick validate`.
- Tier-by-tier findings, warnings, and limitations.
- Recommended Methods and Limitations language.
- Evidence pointers to checked files, benchmarks, or field data.
- Follow-up validation actions when claims exceed available evidence.

## Workflow
<!-- id: messick/workflow -->

Canonical sequence:

1. Identify the study output and the claim it supports.
2. Choose validation tiers based on available evidence.
3. Run Tier 1 checks for internal sanity and prompt/result consistency.
4. Add Tier 2 benchmark comparisons when data exists.
5. Add Tier 3 human or field validation only when real reference data is available.
6. Run `messick validate ...` with the chosen inputs.
7. Translate the validation result into report-ready claims and limitations.

## Worked examples
<!-- id: messick/examples -->

### Validating a simulated survey
<!-- id: messick/example-simulated-survey -->

User: "The agent survey says 68% of customers would switch. Can I put that in the report?"

Agent: "Let's validate before reporting it as a customer estimate. I’ll run internal checks on the EDSL outputs, then compare the 68% to your human pilot or any prior survey if available. If we only have internal checks, the report should call this an exploratory simulated estimate."

User: "We have last quarter’s survey: 61% said they would consider switching."

Agent: "Good. That supports a Tier 2 comparison. I’ll validate missingness and response consistency, then report the synthetic estimate as directionally aligned with the prior benchmark."

```bash
messick validate \
  --results data/agent_survey_results.json \
  --benchmark data/q4_customer_survey.csv \
  --claim "customers would consider switching"
```

Output: validation findings and bounded report language.

### Internal-only validation
<!-- id: messick/example-internal-only -->

```bash
messick validate \
  --results .oneheart/runs/pilot/results.json \
  --tier internal
```

Output: sanity-check findings and a limitation that no external benchmark was used.

## Quick command reference
<!-- id: messick/commands -->

For full options, run `messick validate --help`.

| Command | Purpose |
|---|---|
| `messick validate` | Run tiered validation checks against study outputs and optional benchmarks. |

## Common pitfalls
<!-- id: messick/pitfalls -->

- Passing Tier 1 checks does not mean the synthetic results match humans; it means the run is internally coherent.
- Benchmark mismatch is common: compare populations, wording, timing, and response options before interpreting differences.
- Validation should target the claim, not every incidental output file.
- A failed validation is still useful; it narrows what can be responsibly claimed.

## Cross-references
<!-- id: messick/xrefs -->

- Upstream: validate outputs from [labeling](#labeling/labeling), [manning](#manning/manning), [oneheart](#oneheart/oneheart), [saldana](#saldana/saldana), or EDSL studies.
- Downstream: use [gutenberg](#gutenberg/gutenberg) to compile validation language into reports and [tufte](#tufte/tufte) to QA validation figures.
- Adjacent methods: [bewley](#bewley/bewley) supports qualitative validation of themes and quotes.
