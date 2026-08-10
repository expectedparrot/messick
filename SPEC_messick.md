# Messick specification

Status: Draft

Target package: `messick`

## 1. Purpose

Messick is an agent-first package for pretesting, revising, and validating
structured research instruments represented primarily as EDSL `Survey`
artifacts.

Messick helps a researcher answer:

1. What construct, response process, interpretation, or decision is this
   instrument intended to support?
2. Can respondents understand and complete the instrument as intended?
3. Are response options, instructions, ordering, and branching behavior sound?
4. Do multi-item scales behave coherently in pilot responses?
5. What evidence supports or challenges each intended interpretation and use?
6. Which questions should be retained, revised, rescored, reordered, or removed?
7. Given the available budget and stakes, what is the strongest defensible
   conclusion now, and what optional additional evidence would most improve it?

Most Messick workflows use simulated EDSL respondents as an inexpensive
pretesting layer. Messick also accepts human responses collected through
Humanize. Every finding must retain its evidence source so simulated results
cannot be mistaken for evidence about human measurement performance.

A workflow does not fail merely because human responses are unavailable.
Messick must support a complete, useful simulation-only workflow and clearly
state what was learned, what remains uncertain, and which claims would require
human evidence. Human fielding is an optional escalation chosen according to
budget, risk, and intended use—not a universal gate.

Messick owns instrument-testing state, evidence, issue adjudication,
psychometric diagnostics, revision history, validation claims, and canonical
analytic artifacts. EDSL owns survey objects and inference. Humanize owns human
fielding. `ep` owns generic inspection, costing, paid execution, workflow gates,
and final report checks. The research agent owns the final branded narrative.

## 2. Design principles

### 2.1 Validate interpretations and uses, not instruments in the abstract

Messick never declares that an instrument is globally “valid.” Validation is
always attached to a proposed interpretation or use, such as:

- “The mean of items q1–q6 is interpreted as workplace trust.”
- “Scores are used to compare departments.”
- “A score below 3 triggers an interview follow-up.”

The same evidence may support one use and fail to support another.

### 2.2 Simulated respondents are pretesting evidence

Simulated-agent responses can identify:

- ambiguous wording;
- plausible alternative interpretations;
- broken or weak response options;
- obvious branching failures;
- redundancy;
- reverse-scoring mistakes;
- likely ceiling or floor effects;
- persona-insensitive items;
- candidate response-process and cultural problems.

They do not establish that humans will interpret items identically, reproduce
the same factor structure, or exhibit the same reliability, prevalence,
subgroup differences, or treatment effects.

Messick must label simulation-only conclusions as pretesting or simulated-pilot
findings. It must never call them human validation.

### 2.3 Human evidence remains distinct

Human responses collected through Humanize are first-class evidence sources.
Messick records the survey revision, fielding artifact, collection period,
sample description, response count, provenance, and any relevant Humanize
identifiers.

Human and simulated responses are never silently pooled. Combined analyses
must explicitly name sources and justify pooling.

### 2.4 Evidence requirements are practical and proportional

Messick uses an evidence ladder rather than a mandatory human-validation gate:

1. Static checks are the cheapest baseline and may be sufficient to catch
   structural defects.
2. Simulated cognitive and behavioral pretests are the default evidence tier.
   They can produce a completed pretest, a revised instrument, and a bounded
   readiness recommendation.
3. Human piloting is recommended when affordable and warranted by the stakes,
   but it is not required to complete a Messick project.
4. Consequential claims about human reliability, dimensionality, prevalence,
   subgroup differences, or decision accuracy require suitable human evidence.

The CLI must never block report generation, issue adjudication, revision, or
simulation-level completion because human evidence is absent. It may mark a
specific human-dependent claim as unevaluated and recommend a human pilot with
an explicit rationale, minimum useful design, and approximate resource needs.

### 2.5 Package-owned state, EDSL-owned execution

Messick may create portable EDSL `Jobs.ep` artifacts but never performs model
inference itself. The required boundary is:

```text
messick job generate
→ ep inspect <exact-Jobs.ep>
→ ep jobs cost <same-Jobs.ep>
→ explicit approval
→ ep run <same-Jobs.ep> --output <Results.ep>
→ messick results ingest <exact-Results.ep>
```

Human fielding similarly remains outside Messick:

```text
messick fielding plan
→ Humanize deployment and human participation
→ exported or referenced human response artifact
→ messick responses ingest --source-type human ...
```

### 2.6 Append-only evidence and replay-safe ingestion

Raw surveys, Jobs, Results, human exports, and evidence records are immutable.
Revisions create new IDs. Re-ingesting the same artifact is idempotent and does
not create duplicate evidence.

### 2.7 The package guides; it does not replace judgment

Messick calculates deterministic diagnostics and organizes evidence. It does
not automatically remove items, infer the intended construct, decide whether a
social consequence is acceptable, or turn a threshold into a scientific rule.

## 3. Scope

### 3.1 In scope

- Importing and versioning EDSL Survey instruments.
- Defining intended constructs, score interpretations, populations, and uses.
- Static question and response-option inspection.
- Per-question textual-complexity diagnostics and estimated completion time,
  aggregated across reachable survey paths.
- Branching and skip-logic graph analysis.
- Cognitive pretesting with simulated respondents.
- Behavioral pilot administration to simulated respondents.
- Human pilot response ingestion from Humanize.
- Response-process evidence and question-level issue tracking.
- Reverse scoring and scale definitions.
- Missingness, completion, burden, and order diagnostics.
- Classical reliability analysis and item diagnostics.
- Exploratory dimensionality analysis when sample size permits.
- Comparison of simulated and human pilot behavior without implying equivalence.
- Instrument revision and version comparison.
- Claim-specific validation evidence and limitations.
- Canonical tables, plots, manifests, and bounded report context.

### 3.2 Out of scope

- Executing paid model inference.
- Hosting or operating Humanize.
- Recruiting human participants.
- Qualitative coding of long interview transcripts; use Bewley.
- Generic row labeling; use Labeling.
- Constructing or calibrating digital-twin populations; use Zwill or Umriss.
- General population-validation claims; use the dedicated population-validation
  package when created.
- Full confirmatory factor analysis, item-response theory, differential item
  functioning, measurement invariance, or norming in the first release.
- Automatically certifying an instrument for consequential use.
- Writing the final branded study report.

## 4. Principal workflows

### 4.1 Static instrument review

Use when an instrument exists but no responses have been collected.

1. Initialize a Messick project.
2. Import an EDSL Survey revision.
3. Define intended interpretations and uses.
4. Inspect question wording, options, instructions, ordering, and branching.
5. Run deterministic branch coverage and schema checks.
6. Record and adjudicate item-level issues.
7. Create a revised Survey artifact.
8. Compare revisions and validate readiness for pilot testing.

### 4.2 Simulated cognitive pretest

Use simulated respondents to probe how questions may be interpreted.

1. Select an instrument revision and target respondent descriptions.
2. Generate a Messick-owned cognitive-pretest Jobs artifact.
3. Inspect, cost, and obtain approval through `ep`.
4. Run with `ep run` and ingest the exact Results artifact.
5. Normalize findings to question IDs and response-process categories.
6. Review representative evidence and adjudicate issues.
7. Revise the instrument or attest that issues are accepted.

The cognitive-pretest job may ask simulated respondents to:

- paraphrase the question;
- explain how they selected an answer;
- identify ambiguous terms;
- describe missing response options;
- identify assumptions or sensitive implications;
- distinguish the intended construct from adjacent constructs;
- describe recall and judgment difficulty.

These responses are diagnostic hypotheses, not observations of real human
cognition.

### 4.3 Simulated behavioral pilot

Administer the actual Survey to an approved simulated population.

1. Register an AgentList and ModelList or package-generated Jobs artifact.
2. Run a low-cost sample before a larger simulated pilot.
3. Ingest Results with respondent, model, and survey-revision provenance.
4. Analyze distributions, missingness, completion, branch traversal, item
   behavior, scale coherence, and known-group sensitivity.
5. Record issues without claiming that human behavior has been validated.

### 4.4 Optional human pilot through Humanize

Use this workflow when the user has access to human respondents and the
intended claims justify the added cost. It extends, but is not a prerequisite
for completing, the simulation-first workflow.

1. Freeze the Survey revision intended for fielding.
2. Generate a fielding plan containing the exact Survey artifact and relevant
   Humanize instructions.
3. Deploy and collect responses outside Messick.
4. Ingest the resulting human response artifact or supported Humanize reference.
5. Record sample and fielding provenance.
6. Run completion, missingness, branch, response-option, reliability, burden,
   and dimensionality diagnostics as appropriate.
7. Compare with simulated pilot evidence only through an explicit comparison.
8. Update validation claims and instrument decisions.

### 4.5 Optional mixed simulated and human comparison

Messick may compare sources on:

- item distributions;
- missingness and refusal;
- branch traversal;
- completion and burden proxies;
- item-total relationships;
- reliability estimates;
- factor-loading patterns;
- known-group directions;
- identified comprehension issues.

The output must show simulated and human estimates separately, identify
non-comparable conditions, and state which claims remain unsupported.

## 5. Project and data model

### 5.1 Visible project files

```text
<project>/
  messick.yaml
  instruments/
    instrument_v001.ep
    instrument_v002.ep
  edsl_jobs/
    cognitive_pretest_v001.ep
    behavioral_pilot_v001.ep
  data/
    results/
    human/
  analysis/
    messick_report_context.json
  .messick/
    project.json
    events/
    instruments/
    intents/
    sources/
    runs/
    issues/
    decisions/
    scales/
    analyses/
    comparisons/
    validations/
    reports/
    cache/
```

Users and agents must not edit `.messick/` directly.

### 5.2 Core entities

#### Project

- `project_id`
- title and research context
- created time and actor
- current instrument revision
- current workflow revision

#### Instrument revision

- stable `instrument_id`
- monotonic revision ID
- exact Survey artifact path and SHA-256
- ordered question IDs and hashes
- branching graph hash
- parent revision
- change summary
- status: draft, pilot-ready, human-fielded, retired

Question identity must survive ordinary wording changes when the researcher
intends continuity. Splits, merges, and replacements require explicit lineage.

#### Validation intent

- `intent_id`
- construct or target attribute
- intended score interpretation
- intended population
- intended use or decision
- consequences and error risks
- selected evidence tier: static, simulation, or human
- minimum evidence needed for the current goal
- optional higher-value evidence and its expected benefit
- acceptance criteria or tolerances
- status: proposed, active, supported, challenged, inconclusive, not-evaluated,
  requires-human-evidence

#### Evidence source

- `source_id`
- type: static, simulated-cognitive, simulated-behavioral, human, benchmark
- instrument revision
- source artifact and hash
- collection or run provenance
- population/sample description
- model and agent provenance when simulated
- Humanize provenance when human
- row/respondent count
- comparability notes

#### Question issue

- `issue_id`
- instrument revision and question ID
- category
- severity
- evidence-source IDs
- evidence excerpts or statistics
- description
- proposed resolution
- disposition: open, accepted, revise, remove, rescore, reorder, no-action
- rationale and actor
- superseding issue or revision

Initial issue categories:

- comprehension
- retrieval/recall
- judgment
- response-mapping
- missing-option
- ambiguity
- construct-irrelevance
- construct-underrepresentation
- sensitivity/social-desirability
- translation/cultural-fit
- ordering/context
- branching
- burden/fatigue
- redundancy
- scoring
- statistical-item-performance
- accessibility

#### Scale definition

- `scale_id`
- instrument revision
- item question IDs
- scoring direction
- reverse-scored items
- permitted missingness
- aggregation rule
- intended dimensionality
- associated validation intents

#### Analysis

- `analysis_id`
- analysis type and version
- source IDs
- instrument and scale revisions
- parameters and seed
- artifacts
- warnings and limitations
- software versions

#### Decision

- affected question, scale, or instrument
- action
- rationale
- evidence IDs
- actor and timestamp
- resulting revision

## 6. Configuration

`messick.yaml` is human-readable configuration, not the event ledger.

Illustrative configuration:

```yaml
schema_version: 1
project:
  title: Workplace trust instrument pretest

instrument:
  path: instruments/instrument_v001.ep

population:
  description: Full-time US employees at organizations with 100+ workers

intents:
  - id: trust_mean
    construct: workplace trust
    interpretation: Mean of trust_1 through trust_6 reflects workplace trust
    use: Compare broad organizational groups in exploratory research

scales:
  - id: workplace_trust
    items: [trust_1, trust_2, trust_3, trust_4, trust_5, trust_6]
    reverse_scored: [trust_4]
    range: [1, 7]
    missing: require_complete
    expected_dimensions: 1

pretest:
  cognitive_prompts:
    - paraphrase
    - answer_process
    - ambiguity
    - missing_options
  simulated_sample_size: 30

analysis:
  reliability: true
  dimensionality: exploratory
```

Every generated artifact records the exact configuration snapshot and hash.

## 7. CLI contract

### 7.1 Global behavior

```text
messick [--project-dir PATH] [--human] COMMAND ...
```

- JSON is the default output.
- `--human` renders concise human-readable output without changing semantics.
- Every response uses a versioned envelope.
- Errors are structured and nonzero.
- Unknown commands and options fail immediately.
- Mutations support optional revision guards.
- No CLI command runs model inference or deploys a human survey.

### 7.2 Agent commands

```text
messick agent guide
messick agent next
messick agent status
messick agent history
messick agent docs list
messick agent docs show <topic>
```

`agent next` is the canonical control surface for an automated research agent.
It returns one recommended action plus bounded alternatives. Returned
actions must include complete `cwd`, `argv`, mutation status, approval
requirements, and a reason. If task-specific content must be supplied through a
file, the response includes a machine-readable JSON schema and an example.

`agent next` must be state-aware, deterministic for the same project state, and
cheap: it performs no model inference, remote lookup, or unbounded artifact
inspection. After every mutation, its next recommendation must reflect the new
state. When no action remains, it returns an explicit terminal state rather than
inventing more work.

### 7.3 Project and instrument commands

```text
messick init --title ...
messick validate [--strict]
messick instrument import --survey <Survey.ep> [--message ...]
messick instrument show [--revision ...]
messick instrument compare --from ... --to ...
messick instrument export --revision ... --output <Survey.ep>
messick instrument set-current --revision ...
```

### 7.4 Intent and scale commands

```text
messick intent add --input intent.json
messick intent list
messick intent show <intent-id>
messick scale add --input scale.json
messick scale list
messick scale show <scale-id>
```

### 7.5 Inspection and deterministic testing

```text
messick inspect
messick branching analyze
messick branching paths
messick burden analyze
messick burden show --question <question-id>
messick burden compare --from <revision-id> --to <revision-id>
messick options analyze
messick scoring validate
```

`burden analyze` returns both question-level and survey-level estimates. It must
write a machine-readable artifact containing the components, assumptions, and
uncertainty for every question rather than returning only a total duration.

### 7.6 Simulated pretesting

```text
messick pretest plan --mode cognitive|behavioral
messick job generate --plan <plan-id> --output <Jobs.ep>
messick results ingest --plan <plan-id> --results <Results.ep>
messick pretest analyze --source <source-id>
```

`job generate` is model-free unless an explicit ModelList has been registered.
The generated response must include exact handoff commands for `ep inspect`,
`ep jobs cost`, and the eventual approved `ep run`.

### 7.7 Human responses

```text
messick fielding plan --revision <revision-id>
messick responses ingest --source-type human --input <artifact> \
  --instrument-revision <revision-id> --input-format humanize|results-ep|csv
messick responses show <source-id>
```

Humanize-specific adapters may resolve supported identifiers or exports, but
Messick must preserve a local immutable manifest of what was ingested.

### 7.8 Issues and decisions

```text
messick issue list [--question ...] [--status ...]
messick issue show <issue-id>
messick issue add --input issue.json
messick issue adjudicate <issue-id> --decision revise|remove|accept|no-action \
  --rationale ...
messick decision list
```

### 7.9 Analysis

```text
messick scale analyze --scale <scale-id> --source <source-id>
messick scale compare --scale <scale-id> --sources <source-id>...
messick source compare --left <source-id> --right <source-id>
messick validation evaluate --intent <intent-id>
messick validate [--strict]
```

### 7.10 Reporting

```text
messick report context --output analysis/messick_report_context.json
messick report template --output analysis/messick_report_template.md
```

Messick does not write `writeup/report.md` or `writeup/report.html`.

## 8. JSON envelope

Every command returns:

```json
{
  "schema_version": "1.0",
  "command": "messick ...",
  "argv": ["messick", "..."],
  "status": "ok",
  "project_root": "/absolute/path",
  "revision": 12,
  "data": {},
  "artifacts": {},
  "warnings": [],
  "errors": [],
  "next_steps": []
}
```

Errors include stable codes, messages, context, and actionable hints. Large
tables are written as artifacts and summarized in `data`; they are not dumped
into the agent context.

## 9. Analysis requirements

### 9.1 Deterministic instrument checks

- unique and stable question names;
- supported question types;
- option and scale-bound consistency;
- duplicate or near-duplicate options;
- required prompts and instructions;
- unreachable branches;
- references to nonexistent questions or options;
- branch cycles unless explicitly supported;
- uncovered terminal paths;
- inconsistent scale direction or reverse scoring;
- invalid piping or templating references.

### 9.2 Question complexity and estimated burden

Messick estimates burden for each question and for every reachable survey path.
For each question it reports:

- estimated seconds as a range and a central estimate;
- reading time;
- comprehension and interpretation time;
- recall or information-retrieval time;
- judgment and option-selection time;
- response-entry time, including an explicit assumption for open text;
- conditional overhead from instructions, grids, piping, and branching;
- confidence in the estimate and the basis used to derive it.

Survey-level output includes the shortest, typical, and longest reachable path,
with total estimated time and the questions contributing most to burden. The
report must make clear that pre-fielding times are estimates, not observed human
completion times. When timestamped human responses are later available, Messick
reports observed medians and percentiles separately and may show calibration
error against the earlier estimates.

Textual-complexity checks operate at the question level and include:

- word, sentence, and option length;
- reading level and syntactic complexity;
- uncommon, technical, abstract, or undefined terms;
- negation, double negation, and logically nested conditions;
- double-barreled or multi-part questions;
- vague quantifiers and ambiguous reference periods;
- excessive introductory text or instructions;
- mismatch between prompt complexity and the intended population;
- response-option complexity and overlap.

Complexity metrics are diagnostics, not mechanical rewrite rules. Readability
scores alone must not label a question defective. Recommendations should quote
or identify the feature that created difficulty and propose a concrete revision.
Population-sensitive judgments may be strengthened with simulated cognitive
pretests, but must retain their simulated-evidence label.

Timing assumptions and thresholds are configurable. Defaults must be documented,
versioned, and included in the result artifact so that estimates are reproducible.

### 9.3 Response diagnostics

Diagnostics use declared response bounds and Survey metadata, not observed
sample extrema.

- missingness and refusal by item/source/subgroup;
- out-of-range or invalid values;
- option utilization;
- floor and ceiling rates;
- variance and entropy;
- completion by branch;
- straightlining and patterned response where applicable;
- order and position diagnostics where a design permits them;
- simulated persona sensitivity;
- human completion and burden indicators when available.

### 9.4 Scale diagnostics

Initial release:

- scoring and reverse-scoring validation;
- item means, SDs, missingness, floors, and ceilings;
- inter-item correlations appropriate to declared item type;
- corrected item-total correlations;
- Cronbach's alpha with uncertainty where supported;
- McDonald's omega when dependencies permit;
- alpha/omega if item deleted;
- exploratory eigenvalues and factor loadings;
- explicit sample-size and identifiability diagnostics;
- analysis artifacts sufficient to reproduce calculations.

Thresholds are configurable warnings, not automatic scientific decisions.

### 9.5 Source comparison

Simulation-versus-human comparison must:

- retain separate estimates;
- show sample sizes and uncertainty;
- identify population, wording, timing, and administration differences;
- report direction and magnitude rather than a binary match;
- avoid equivalence claims without a prespecified equivalence design;
- state which validation intent each comparison informs.

## 10. Validation statuses

Validation is evaluated per intent and against its declared evidence tier:

- `supported`: required evidence exists and no blocking challenge remains;
- `challenged`: evidence conflicts with the intended interpretation or use;
- `inconclusive`: available evidence at the selected tier is insufficient or
  mixed;
- `not_evaluated`: the intent was not evaluated at the selected tier;
- `requires_human_evidence`: the proposed claim concerns human measurement
  performance and cannot be supported by simulation alone.

`requires_human_evidence` limits that claim; it is not a failed project gate. A
simulation-only project may be complete when its declared goal is instrument
pretesting rather than validation in a human population.

Strict project validation checks process completeness, not scientific truth.
For example, it may verify that every severe issue is adjudicated and every
active intent has an evidence status. It must not turn a passing process check
into a claim that the instrument is valid.

## 11. Reporting contract

The report context includes:

- instrument purpose and revision;
- intended constructs, interpretations, populations, and uses;
- evidence-source inventory clearly separating simulated and human sources;
- deterministic findings;
- question-level textual-complexity findings;
- per-question burden estimates and their components;
- shortest, typical, and longest path completion-time estimates;
- observed human timing, when available, kept distinct from estimated timing;
- question-level issue counts and dispositions;
- scale diagnostics with caveats;
- source comparisons;
- supported, challenged, inconclusive, and unevaluated intents;
- revision history;
- unresolved limitations and optional next evidence ranked by expected value;
- canonical artifact paths and hashes.

Recommended language must be proportional to evidence. Examples:

- Simulation only: “A simulated cognitive pretest identified candidate wording
  and response-option problems. Human interpretation has not been established.”
- Human pilot: “In a human pilot of N=84 from the intended population, the scale
  showed acceptable internal consistency; dimensionality evidence remained
  inconclusive.”
- Mixed: “Simulated and human pilots agreed on the direction of two item
  problems but differed materially in response distributions.”

## 12. Safety, privacy, and authorization

- Never expose private human responses to model inference without explicit
  authorization and an approved data-sharing plan.
- Preserve raw human responses separately from derived findings.
- Support redacted or deidentified cognitive evidence.
- Record whether open text was transmitted to any model or remote service.
- Humanize deployment, invitations, reminders, and publication are external
  side effects and require explicit authorization.
- Simulated respondents must not be described as human participants.
- Consequential uses require explicit review of foreseeable errors and harms.

## 13. Interoperability

### EDSL

- `Survey.ep` is the canonical instrument exchange format.
- `AgentList.ep`, `ModelList.ep`, `Jobs.ep`, and `Results.ep` are preserved as
  durable artifacts where applicable.
- Messick uses public EDSL APIs and `ep` commands; it does not inspect package
  internals.

### Humanize

- Messick produces a fielding plan for a frozen Survey revision.
- Humanize owns deployment and response collection.
- Messick ingests a documented Humanize response export/reference and records
  its provenance.

### Labeling

- Labeling may classify open-ended pretest evidence using a stable rubric.
- Messick remains the owner of instruments, questions, revisions, validation
  intents, and item decisions.

### Bewley

- Bewley may develop inductive themes from cognitive interview material.
- Messick ingests only reviewed, structured findings linked to question IDs.

### Population validation

- A future dedicated package may validate simulated populations against human
  benchmarks.
- Messick consumes those diagnostics when they affect an instrument intent but
  does not duplicate population construction or calibration.

## 14. Package quality and documentation contract

Messick follows the common contract expected of packages used by ep-agent. The
package is not integration-ready merely because its core analysis works.

### 14.1 Required repository surfaces

- `README.md` with purpose, non-goals, installation, a minimal end-to-end
  quickstart, EDSL/`ep` handoff, Humanize's optional role, and links to docs;
- `docs/index.html` as the browsable documentation entry point;
- source documentation for every public command, configuration field, artifact,
  JSON envelope, error code, and analysis definition;
- `examples/` containing at least one small simulation-only project that can be
  run end to end without human data;
- `pyproject.toml` with a working console-script entry point and constrained
  runtime dependencies;
- a committed lockfile for development and reproducible test environments;
- `LICENSE`, `CHANGELOG.md`, and contribution guidance;
- automated unit and integration tests plus CI on supported Python versions.

The README quickstart must begin with an existing EDSL `Survey.ep`, run
deterministic checks, generate and execute a small simulated pretest through the
explicit `ep` handoff, ingest results, and produce bounded report context. It
must not make human evidence appear mandatory.

### 14.2 Documentation requirements

`docs/index.html` must be usable as a static local file and link to:

- a concepts page explaining instruments, revisions, intents, evidence tiers,
  issues, decisions, and analyses;
- CLI reference and copyable workflows;
- JSON schemas and artifact formats;
- analysis-method definitions, assumptions, and limitations;
- an agent-integration guide centered on `messick agent next`;
- troubleshooting and stable error-code guidance;
- simulation-only, Humanize, and mixed-evidence examples.

Human-facing documentation and `messick agent docs` must be generated from, or
tested against, the same canonical command and schema metadata. CI fails when
documented commands, options, examples, or checked-in generated documentation
are stale.

### 14.3 CLI operability and release checks

The installed package must support:

```text
messick --version
messick --help
messick agent next --help
messick doctor
```

`doctor` performs bounded, non-mutating checks of configuration, supported EDSL
APIs, required executables, project readability, schema compatibility, and
optional Humanize availability. Missing optional Humanize configuration is a
capability notice, not a failure.

Each release must pass:

- clean installation into a fresh locked environment;
- README quickstart execution;
- CLI help/documentation parity checks;
- JSON-schema and stable-error-code contract tests;
- exact replay and idempotency tests;
- a package build check excluding caches, local data, generated studies, and
  duplicate `build/` source trees;
- at least one simulation-only end-to-end smoke test.

### 14.4 Thin ep-agent integration

Messick ships or documents enough package-owned guidance that the ep-agent skill
can remain thin. The skill should identify when Messick applies, establish the
project directory, and defer workflow sequencing to `messick agent next`. It
must not duplicate the CLI manual, embed large Python scripts, or become the
source of truth for Messick's workflow.

## 15. Migration from the current prototype

The existing 0.1.0 implementation is not a compatibility constraint.

- Replace the permissive Typer/argparse forwarding interface.
- Remove committed `build/` artifacts.
- Replace `Results.load` and `.json.gz` assumptions with supported `.ep`
  artifact handling.
- Move generic synthetic-population validation concepts to the future
  population-validation package where appropriate.
- Preserve only well-tested elementary diagnostics whose definitions fit this
  specification.
- The first rewritten release may remain `0.x`; no compatibility shim for the
  broken `messick validate` invocation is required.

## 16. Testing strategy

### Unit tests

- Survey import, hashing, revision lineage, and idempotency.
- Question identity across edits, splits, merges, and replacements.
- Branch graph analysis and path coverage.
- Reproducible question-level burden components and path-time aggregation.
- Textual-complexity fixtures covering negation, multi-part wording, reading
  level, ambiguous reference periods, and intended-population mismatch.
- Scale scoring and reverse scoring.
- Reliability statistics against known fixtures.
- Missingness and floor/ceiling calculations using declared bounds.
- JSON schemas and envelope stability.
- Issue adjudication and intent-status transitions.
- Replay-safe Results and human-response ingestion.

### Integration tests

- Generate cognitive-pretest Jobs from a Survey and ingest fixture Results.
- Generate behavioral-pilot Jobs and preserve source provenance.
- Ingest a Humanize-style human response fixture.
- Compare simulated and human sources without pooling.
- Revise an instrument and compare question/branch/scale changes.
- Generate bounded report context.

### Live tests

1. Cognitive-test a short survey with simulated personas and revise it.
2. Test a branched survey and detect a broken or unreachable path.
3. Run a simulated multi-item-scale pilot and identify a reverse-scoring error.
4. Ingest a human pilot and produce human-specific scale diagnostics.
5. Compare simulated and human pilots and produce appropriately bounded claims.

Live-eval acceptance includes tool failures, turns, elapsed time, tokens, agent
cost, inference cost, and substantive artifact quality.

## 17. Delivery milestones

### Milestone 1: state and instrument foundation

- project initialization;
- Survey import/versioning;
- intents and scales;
- agent guide/next/status/history/docs;
- deterministic validation;
- versioned JSON envelope.

### Milestone 2: static and branching diagnostics

- question inspection;
- branching analysis;
- issue ledger and adjudication;
- revision comparison.

### Milestone 3: simulated pretesting

- cognitive and behavioral plans;
- Jobs generation;
- exact `ep` handoff;
- Results ingestion;
- bounded pretest analysis.

### Milestone 4: psychometric analysis and reporting

- scale analyses;
- intent evaluation;
- canonical analysis artifacts;
- report context and template;
- end-to-end live tests.

### Milestone 5: optional human evidence

- fielding-plan artifact;
- Humanize response ingestion;
- human provenance and diagnostics;
- source comparison.

Milestone 5 is an additive integration milestone and does not block a useful
simulation-first release.

## 18. Definition of done

Messick is ready for ep-agent integration when:

- [ ] All public commands return documented versioned JSON envelopes.
- [ ] `agent guide`, `agent next`, `agent status`, `agent docs`, and
  `validate --strict` are agent-usable.
- [ ] The repository includes a tested README quickstart and browsable
  `docs/index.html` whose commands match the installed CLI.
- [ ] A clean locked installation, package build, and supported-version CI pass.
- [ ] Survey revisions and evidence sources are immutable and traceable.
- [ ] Simulated and human findings cannot be confused or silently pooled.
- [ ] Paid inference always uses the explicit Messick → `ep` handoff.
- [ ] Humanize fielding remains an optional, explicit external workflow.
- [ ] Instrument issues and decisions are auditable.
- [ ] Every question receives an inspectable burden estimate with component
  timings, uncertainty, and versioned assumptions.
- [ ] Reachable paths receive aggregate completion-time estimates without
  confusing estimates with observed human timing.
- [ ] Scale calculations reproduce tested fixtures.
- [ ] Validation status is claim/use-specific rather than global.
- [ ] Package report output is a bounded handoff, not the final branded report.
- [ ] The three simulation-first live workflows pass with clean execution.
- [ ] Human and mixed-source workflows pass when optional fixtures or live-test
  resources are available; their absence does not block a release.
- [ ] ep-agent can replace the current psychometric and relevant pretesting
  mechanics with a thin Messick owner skill.
