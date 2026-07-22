# Messick — Agent Operating Guide

## When to invoke

After `recipe:run-with-llm-agents` produces `data/results.json.gz`, and
**before** writing the report. Validation is part of the methodology;
skipping it produces reports whose claims aren't underwritten.

## The three tiers, and which to run

| Tier | Needs | What it tells you |
|---|---|---|
| 1. Internal sanity | only `data/results.json.gz` | "did the run technically succeed?" — `None` rates, segment coverage, format compliance, no all-same-answer epidemics |
| 2. Comparison | a benchmark dataset (CSV / JSON of empirical proportions) | "does the LLM agree with humans on questions where we know the answer?" |
| 3. Field | an out-of-sample real-population test | "does the LLM-agent finding predict behavior in the wild?" |

Run **Tier 1 always**. Run **Tier 2 if the study makes any claim about
real-world behavior or attitudes**. Tier 3 is rare and only relevant
for high-stakes deployment work.

## Operating sequence

1. **Tier 1 — internal sanity.**

   ```bash
   messick validate tier1 --results data/results.json.gz --out analysis/validation/
   ```

   Produces:
   - `tier1_summary.md` — pass/fail summary with details on any
     failures.
   - `tier1_per_question.csv` — per-question `None` rate, response
     diversity, format-failure flags.

   If anything fails: do not proceed to Tier 2 or to the report. Most
   Tier 1 failures mean the run was technically broken; loop back
   to `recipe:run-with-llm-agents` Step 7 (post-run review).

2. **Tier 2 — comparison.** Requires a benchmark JSON file mapping
   `question_name` → list of empirical proportions in option order.

   ```bash
   messick validate tier2 \
       --results data/results.json.gz \
       --benchmark benchmark.json \
       --out analysis/validation/
   ```

   Produces:
   - `tier2_comparison.csv` — per-question TVD between LLM
     distribution and benchmark.
   - `tier2_summary.md` — overall agreement, questions with notable
     disagreement, recommendation.

   A typical "good" Tier 2 result has total TVD < 0.10 across all
   benchmark questions. > 0.20 is a red flag — the LLM is
   systematically disagreeing with humans on something the benchmark
   already established.

3. **Tier 3 — field validation.** Highly study-specific. Document
   the protocol in the report's Methods section if used.

## What to put in the report's Methods section

Whichever tier(s) you ran, the report must say so:

> "Internal validation (Tier 1, Messick framework): all questions
> passed at <5% None rate; no format-failure clusters." 

> "Comparison validation against the [benchmark name] dataset: TVD
> = 0.07 across [N] benchmark questions, indicating substantial
> agreement."

If a tier failed, name the failure and explain what was done about
it. Hiding failed validations is worse than not validating; it
misleads the reader into trusting findings that the study does not
actually underwrite.

## Common pitfalls

- **Skipping Tier 1 because the run "looked fine."** Format-failure
  rates can be misleadingly low *across* a survey while one specific
  question is silently producing 40% `None`. Tier 1 finds those.
- **Treating Tier 2 disagreement as LLM failure.** Sometimes the
  benchmark is wrong (old, nonrepresentative, small N). When TVD is
  high, *investigate* before concluding either way.
- **Cherry-picking Tier 2 questions.** Use the full benchmark
  question set, not the subset that agrees with the LLM.

## Cross-references

- `library:methods/response-validation.md` — full conceptual
  reference for the framework.
- `recipe:run-with-llm-agents` — the upstream run.
- `recipe:analyze-results` — analyze validated `Results` for the
  writeup.
- `recipe:write-report` — Methods section requirements.
