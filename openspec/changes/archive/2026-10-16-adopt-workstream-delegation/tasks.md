# Tasks

## 1. Prerequisite

- [x] 1.1 Confirm `add-claude-code-orchestration` has been archived through its own workflow. Verify all three:
  - `openspec list` no longer shows it;
  - `openspec/specs/development-orchestration/spec.md` contains "Host-specific native dispatch";
  - `openspec/specs/orchestration-run-log/spec.md` contains "First-pass route outcome".

  Then confirm `openspec validate adopt-workstream-delegation --strict` no longer reports that archive would refuse either delta.

## 2. Coordinator: delegation and workstreams

- [x] 2.1 In `subagents/clanker-orchestration-nation.md` ("Select roles and hand off"), add the delegation threshold:
  - the parent keeps only fixes it has already diagnosed that take a few calls, plus its own git, OpenSpec, and log work;
  - it logs a one-line reason for any work it keeps;
  - the tier breaks ties.

  Verify with a new assertion in `tests/test_orchestration_guidance.py`.
- [x] 2.2 In the same section, describe workstreams and verify each rule with guidance assertions:
  - each owns a code area recorded as file ownership, with one lead role and optional extra role checklists;
  - each has at most one thread at a time;
  - continued assignments restate ownership and any spec or design revisions;
  - boundaries split only with an up-front contract and substantial work on both sides;
  - workstreams never own overlapping files.
- [x] 2.3 Add the workstream route rule:
  - the route is resolved once at thread start, from the lead role and the hardest expected tier;
  - continued assignments keep the thread's model and effort;
  - the parent never changes a route on its own; when a thread struggles, the parent continues it, takes the fix over, or asks the user.

  Verify with guidance assertions.
- [x] 2.4 Add the retirement rules:
  - retire a thread after parent verification with no follow-up pending;
  - retire it as `blocked` when its work is abandoned, or left unfinished when the run ends blocked or interrupted;
  - a thread waiting on the user stays active;
  - leave compaction to the host default and record it when observed;
  - continue a reachable retired thread, otherwise start a new one from a parent summary.

  Verify with guidance assertions.
- [x] 2.5 In "Review and integrate", add reviewer recheck reuse:
  - the original native reviewer does its single recheck, with the finding IDs, the fix diff, and a regression check of the changed lines;
  - use a fresh reviewer when the spec, design, or scope changed;
  - external cross-review is unchanged.

  Verify with guidance assertions.
- [x] 2.6 Add the rule that browser QA and long acceptance work run in a worker that owns the browser state, unless the user explicitly directs the parent. The parent keeps the evidence states. Verify with guidance assertions.
- [x] 2.7 Rework the capacity text so thread reuse follows workstreams and reviewer rechecks while keeping the capacity-rejection rule. Update `test_moved_dispatch_text_lives_in_the_codex_host_reference` to match the new split between the coordinator and host text. Verify that `python3 -m unittest tests.test_orchestration_guidance` passes, including the harness-neutral coordinator check.
- [x] 2.8 Add one or two sentences on workstreams to the README's "Orchestration Nation Hosts" section. Verify the README wording matches the coordinator's terms.

## 3. Run log and analysis ledger

- [x] 3.1 In "Keep a concise run log", require every block and ledger row to take its time from the host clock at write time, for example `date` in the same append command. Verify with a guidance assertion.
- [x] 3.2 Document the ledger:
  - `.clanker/orchestration-ledger.csv`, with a header row written when the file is created;
  - the 14 columns in order, including `followup_kind`;
  - the five event types;
  - `followup_kind` set to `defect` or `scope` on `assign-continued` rows, and empty cells otherwise;
  - a new versioned file whenever the columns change;
  - the Python `csv` one-line append command.

  Verify that the documented command, run against a temporary file with a detail containing a comma and a quote, reads back with `csv.reader` as exactly 14 columns.
- [x] 3.3 Replace the closing route-outcome table text with outcomes on `retire` rows:
  - define `first-pass`, `revised`, `rerouted`, and `blocked`;
  - record the defect source;
  - take observed model, effort, and final context from runtime evidence, or `unknown`;
  - keep the narrative completion entry.

  Update `test_run_log_procedure_records_settings_and_route_outcomes` to assert the ledger terms instead of "route-outcome table". Verify the guidance tests pass.
- [x] 3.4 Add a short README note in "Orchestration Nation Hosts" that each run writes the daily `.clanker/<date>-orchestration-nation.md` log plus rows in `.clanker/orchestration-ledger.csv` for spreadsheet analysis. Verify the README and coordinator name the same paths.

## 4. Host references and dispatch procedure

- [x] 4.1 In `subagents/hosts/claude/host.md` ("Concurrency and worker reuse"):
  - replace "start a new worker" with the mechanics: find threads with `ListAgents`, continue one with `SendMessage`, and the continued worker keeps the model and effort it was started with;
  - keep the concurrency limit and capacity-rejection rule;
  - document a jq command that reads `message.model`, `effort`, the last call's context size, and any `compact_boundary` entries from a subagent transcript.

  Verify with host-reference assertions, and check that the jq command prints the expected values against one saved NA-358 subagent transcript.
- [x] 4.2 In `subagents/hosts/codex/host.md`, reduce reuse to mechanics: continue a workstream's idle worker through the collaboration tools, keeping the concurrency and capacity text and the observed-settings rule. Verify with host-reference assertions.
- [x] 4.3 In `subagents/routing/usage.md` (Dispatch procedure), state these and verify with a guidance assertion:
  - routes are resolved once per workstream at thread start;
  - continued assignments refer to the workstream's resolver JSON and still state the readable settings line;
  - no new resolver request is made for a follow-up.

## 5. Worker definition

- [x] 5.1 In `subagents/claude/clanker-orchestration-worker.md`, add to the body that a worker accepts continued assignments, where restated ownership and stated revisions supersede its earlier brief. Leave the frontmatter unchanged. Verify `test_worker_is_generic_and_cannot_delegate` and the installer tests (`python3 -m unittest tests.test_cross_review_installers`) pass.

## 6. Integration

- [x] 6.1 Run `python3 -m unittest tests.test_orchestration_guidance tests.test_cross_review_installers` and `openspec validate adopt-workstream-delegation --strict`. Both must pass.
- [x] 6.2 With user approval, reinstall both hosts with the existing installers (`./wrangle.sh`). Verify that `diff -q` shows each installed `SKILL.md`, `references/host.md`, and worker definition matching the branch sources.
- [x] 6.3 With user approval (one live model call), check that `SendMessage` continues a finished background Claude worker on its original model and effort, confirmed from the worker transcript's `message.model` and `effort`. Record the result in this change. If continuation fails, record that the new-thread-from-summary path applies.
