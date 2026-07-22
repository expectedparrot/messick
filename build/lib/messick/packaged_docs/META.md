---
name: messick
description: >
  Validate that an LLM-agent study's results are credible before publishing.
  Three tiers: internal sanity checks (no `None` epidemic, sensible
  variance, no format failures), comparison against a benchmark dataset, and
  field validation against new human data. Use after running an LLM-agent
  study and before reporting findings.
tags:
  - validation
  - quality-check
  - methods
  - quantitative
invoke: messick
examples:
  - Running internal sanity checks on a freshly-finished EDSL Results.
  - Comparing LLM-agent responses to a benchmark survey result for the same questions.
  - Producing a validation report for the Methods section before publication.
  - Pre-publication review of an LLM-agent study that makes claims about real humans.
  - Building a defensible "yes we checked this" story before external reporting.
---

# messick — is this the right method?

This file is a **fit check for the calling agent**. Read it to decide
whether **tiered construct-validity-style validation** is the right
method for the user's task. Implementation details (commands, file
layouts, thresholds) are out of scope here — those are in the README.

## What the method does

Named for Samuel Messick, the validity theorist who systematized the
requirement that any claim about what a measurement *means* must be
evaluated, not assumed. The package adapts that posture to LLM-agent
studies: a successful run is not, by itself, evidence the findings are
credible.

Three tiers of validation, in order of strictness:

1. **Internal sanity** (no external data). Distributions sensible, no
   mass-`None` failures, expected segments populated, no format-failure
   clusters, no stuck-on-one-option questions. Necessary but not
   sufficient.
2. **Comparison against a benchmark.** Does the LLM-agent distribution
   agree with an established empirical dataset (survey, experiment,
   prior study) for the same questions? Necessary for any claim that
   the result generalizes to humans.
3. **Field validation against new human data.** Does the LLM-agent
   panel predict out-of-sample human behavior on a freshly-collected
   sample? The strongest form; rare and study-specific.

The point: don't publish LLM findings as if they were survey findings
without showing why they should be trusted. Each tier produces an
artifact you can name in a Methods section.

## Use this when

- An **LLM-agent study has finished running** and the results are about
  to be reported externally — paper, client deck, public post, blog.
- The study makes claims that **look like findings about real humans**
  (attitudes, preferences, choices, behaviors) — not just demos of LLM
  capability.
- The user wants a **defensible "yes, we checked this" story** to put
  in Methods, not a hand-wave.
- Pre-publication review: a reviewer, advisor, or client is going to
  ask "how do you know this is real?" and you need an answer.
- The user has a benchmark dataset (Tier 2) or is willing to collect
  human data (Tier 3) and wants to know whether the panel agrees.

## Do not use when

- The study is **internal exploration**, not external publication —
  Tier 1 sanity checks alone are usually enough; the full framework is
  overkill.
- The user wants to **calibrate** an agent panel to humans (iteratively
  fit traits/prompts so the panel matches a target) rather than
  validate a finished panel — see `recipe:manning`. Calibration uses
  validation outputs internally; validation does not produce a
  calibrated panel.
- The user wants a **head-to-head comparison of LLM vs humans** as the
  research question itself (not as a credibility check on a separate
  finding) — see `recipe:compare-llm-vs-humans`.
- The work **hasn't run yet**. Validation is post-run; if the user is
  still designing the study, point them at the run/design recipes
  first.
- The study produces **free-text** as its primary output. Tier 1's
  diagnostics are tuned to closed-form questions; free-text needs a
  separate diagnostic — see `library:methods/free-text-homogeneity.md`.

## Picking which tier

| Situation | Minimum tier |
|---|---|
| Internal exploration, results stay in-team | **Tier 1** |
| Any external report or publication | **Tier 1 + Tier 2** |
| Paper or deck claims the panel reflects a real population | **Tier 1 + Tier 2** |
| Headline claim is "this panel predicts real-world behavior" | **Tier 1 + Tier 2 + Tier 3** |
| High-stakes deployment (a decision will be made on the panel's output) | **Tier 1 + Tier 2 + Tier 3** |

Tier 1 is cheap and always required. Tier 2 needs an existing
benchmark dataset on the same (or close-enough) questions — a public
survey, a prior wave, an internal historical study. If no such
benchmark exists, the user must decide whether to collect one (Tier 3
territory) or caveat the report. Tier 3 requires fielding a real
human study; do not run it casually — it's a separate research project
attached to the original.

## Decision rule for the calling agent

Before dispatching to messick, confirm:

1. The study has **finished running** — there is a `Results` object on
   disk.
2. The user intends to **report or share** the findings outside the
   immediate team, or is doing pre-publication review.
3. The user can name **what would count as the result being credible**
   (sane distributions; agreement with a known benchmark; predicting
   new human data).

If the answer to **"a study is done, results will be reported, and the
user wants evidence the findings should be trusted"** is yes, messick
is the right method. Otherwise route to the appropriate alternative
(`recipe:manning` for calibration, `recipe:compare-llm-vs-humans` for
head-to-head comparison, or the run/design recipes if the work hasn't
happened yet).
