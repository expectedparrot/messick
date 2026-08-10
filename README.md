# Messick

![Messick artwork: a survey-taking parrot between brackets](docs/assets/messick-artwork.png)

**Documentation:** [expectedparrot.github.io/messick](https://expectedparrot.github.io/messick/)

Messick is an agent-first package for pretesting, revising, and validating EDSL
`Survey` instruments. It tracks what an instrument is intended to measure and
support, maintains immutable revisions and evidence provenance, and keeps
simulation findings distinct from evidence about humans.

Messick does not execute model inference, operate Humanize, certify an
instrument globally, or write the final branded research report.

## Copy and paste into Codex or Claude Code

```text
Set up Messick and help me complete an auditable pretest and revision of the
structured research instrument in this repository.

Install `uv` if it is not already available:

python -m pip install --user --upgrade uv

Use `uv` to install Messick in an isolated Python 3.11+ tool environment and
include EDSL's `ep` executable in that same environment:

uv tool install --python 3.11 --upgrade --force \
  --with-executables-from "edsl @ git+https://github.com/expectedparrot/edsl.git@main" \
  "messick @ git+https://github.com/expectedparrot/messick.git@main"

Verify the environment and both command-line interfaces:

uv tool dir --bin
command -v messick
command -v ep
messick --version
messick --help
messick doctor
ep --help

Confirm that `messick` and `ep` resolve from the tool environment reported by
`uv tool dir --bin`. Stop if either resolves to an unexpected installation.

Let EDSL own Expected Parrot authentication. Run `ep auth status`. If
authentication is missing, run `ep auth login` and follow its login flow. If a
redacted profile is already valid, do not log in again. Never print, inspect,
copy, or commit an API key. Then run:

ep profiles current
ep check

Use Messick's CLI as the workflow source of truth:

messick agent guide
messick agent next

If this repository is not already a Messick project, find the intended EDSL
Survey artifact and confirm the project title, intended construct, score
interpretation, population, and use with me before initializing it. Do not
infer a consequential interpretation or decision rule from the item wording.

Run `messick agent next` after every material mutation and follow its single
recommended action. Treat the versioned JSON envelope as authoritative. Do not
edit `.messick/` directly, replace registered artifacts, silently pool evidence
sources, or discard issue and decision history.

Messick may build and verify an exact `Jobs.ep` artifact but never performs
model inference. For any simulated pretest, use the exact path returned by
Messick for `ep inspect`, `ep jobs cost`, and `ep run`. Show me the job summary,
model choice, estimated cost, and output path, and obtain my explicit approval
before `ep run` or any other paid execution. Start with a small pilot.

Always describe simulated respondents and results as simulated pretesting
evidence—not human participants or human validation. Keep human and simulated
responses separate unless an explicit comparison is requested; never pool them
silently. Do not send private human responses or open text to a model without
my explicit authorization and an approved data-sharing plan.

Humanize deployment, invitations, reminders, and publication happen outside
Messick and require my explicit authorization. Messick should produce bounded
report context and evidence artifacts; use those to help me author the final
narrative without claiming that the instrument is globally valid.
```

## Install

```bash
python -m pip install -e '.[edsl]'
messick --version
messick doctor
```

Python 3.11 or newer is required. EDSL is optional for static review and
required for durable `Jobs.ep`, `Survey.ep`, and `Results.ep` integration.

## Simulation-first quickstart

Begin with an existing `Survey.ep` artifact:

```bash
mkdir trust-pretest && cd trust-pretest
messick init --title "Workplace trust pretest"
messick instrument import --survey ../survey.ep
messick intent add --input intent.json
messick validate --strict
messick agent next
```

Commands emit a versioned JSON envelope by default. Add `--human` before the
command for concise formatted output.

Inference will use this explicit handoff when job generation lands:

```text
messick job generate --plan <plan-id> --output edsl_jobs/pretest.ep
ep inspect edsl_jobs/pretest.ep
ep jobs cost edsl_jobs/pretest.ep
# approve the quoted cost
ep run edsl_jobs/pretest.ep --output data/results/pretest.ep
messick results ingest --plan <plan-id> --results data/results/pretest.ep
```

Humanize is optional. Human responses, when supplied, are recorded as a
separate evidence source and never silently pooled with simulations.

See [the published documentation](https://expectedparrot.github.io/messick/),
[the local documentation](docs/index.html), [the specification](SPEC_messick.md),
and [the changelog](CHANGELOG.md).
