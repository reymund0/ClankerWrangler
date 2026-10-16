---
name: clanker-orchestration-nation
description: Coordinate a bounded set of specialists for software work with explicit model routing, OpenSpec continuity, and an append-only run log. Use for multi-role changes, not ordinary single-owner edits.
---

# Clanker Orchestration Nation

Coordinate only the specialists the task needs. The parent owns scope,
integration, OpenSpec artifacts/task state, and the run log. Workers own bounded
assignments and return evidence; they do not recursively delegate.

Use the host's native delegation mechanism, described in the host reference below.
Do not substitute a local model CLI or custom agent framework when native delegation
is unavailable.

## Read the host configuration

Before resolving any route, read `references/host.md` and `routing/host.json` relative
to this coordinator's package. They identify the orchestration host, its preference
file, its native dispatch and capability procedure, and its external reviewer. If
either file is missing or invalid, stop, report the missing prerequisite, and dispatch
no worker. Do not infer the host from the environment. When running from the source
checkout, where host files live under `subagents/hosts/<host>/`, the user must name the
host; read that host's files and pass `--host` to the snapshot command.

## Establish scope

Read the request, repository instructions, relevant code, git state, and existing
OpenSpec state. Identify the requested outcome, risks, dependencies, and authorization.
Handle localized low-risk work directly and record why delegation is unnecessary.

For meaningful features, cross-cutting behavior, uncertain acceptance criteria, or
an existing selected change, use the installed OpenSpec workflows and actual artifact
paths. Ask when the intended change is missing or ambiguous; report unavailable
OpenSpec tooling rather than inventing state or silently creating a competing plan.
Preserve planning-only scope. Mark implementation tasks complete only after integrated
verification; synchronize or archive only when requested or authorized by that workflow.

## Resolve worker settings

Keep the user's parent model and effort. Before the first assignment, read the
**Dispatch procedure** in `routing/usage.md` relative to this coordinator's package
(source checkout: `subagents/routing/usage.md`). It defines the Python 3.10+ prerequisite,
snapshot and resolver commands, request fields, dispatch gates, and evidence capture.
Read its configuration/editor sections only when those details are needed.

Resolve each workstream's route, and each review or planning assignment, through that
procedure using the run snapshot. Disclose the host, the global preference source and
consequential routing limitations; do not silently substitute settings when resolution
or dispatch is blocked.

Use the returned `model` and `effort` as the native tool's model and reasoning-effort
arguments, as the host reference describes. Requested settings are not proof of
observed settings.

## Select roles and hand off

Choose the smallest useful team. Follow the host reference's concurrency limit, counting
any external review; run at most one external review per run at a time.
Parallelize independent work and serialize changes to shared files, interfaces, browser
state, or the reviewed build.

Delegate build work. The parent keeps only fixes it has already diagnosed that it can
finish in a few calls, plus its own git, OpenSpec, and log work, and logs a one-line
reason for each piece of build work it keeps. When these criteria do not settle a case,
straightforward work leans to the parent and involved or demanding work to a workstream.
A small change that needs code the parent has not yet read goes to the workstream that
owns that area.

| Role | Instruction file | Use for |
| --- | --- | --- |
| Architect | `clanker-architect.md` | Boundaries, interfaces, design tradeoffs |
| UI/UX reviewer | `clanker-ui-ux-reviewer.md` | Rendered visuals and interaction evidence |
| Backend | `clanker-backend-developer.md` | APIs, services, integrations, domain logic |
| Data | `clanker-data-engineer.md` | Contracts, queries, integrity, migrations |
| UI implementation | `clanker-ui-developer.md` | Components, forms, client state, layouts |
| QA planning | `clanker-qa-engineer.md` | Acceptance scenarios and verification strategy |
| Test engineer | `clanker-test-engineer.md` | Test implementation and execution |
| Code/security reviewer | Shared `clanker-code-review` skill | Correctness, regressions, spec coverage |
| DevOps | `clanker-devops-engineer.md` | Build, CI, delivery, recovery |
| Performance | `clanker-performance-engineer.md` | Measured bottlenecks and improvements |

The parent owns product outcomes, scope, acceptance criteria, and routine documentation.
Use supplied Claude Design handoffs as UX design context for bounded UI implementation
and independent UI/UX review. Resolve missing material design decisions with the user;
do not automatically invoke Claude Design or assign retired product, documentation,
or UX designer profiles. Retain the shared documentation-update and review skills.

In the source checkout, specialist files sit beside this coordinator in `subagents/`;
installed packages keep them in `references/`. Shared code review is
`skills/clanker-code-review.md` in the checkout or the separate installed skill
(`../clanker-code-review/SKILL.md`). Resolve from the package actually loaded; do not
use retired skills or stale standalone specialist installations.

Read only the selected instructions, verify their names and paths, and require each
worker to read its absolute instruction path, and each extra checklist's path, before domain work. Missing or unreadable
instructions block that assignment; independent work may continue. Specialist guidance
does not override the assignment's phase, ownership, repository rules, or authorization.

Group build work into workstreams by code area. Each workstream owns a set of files,
recorded as its file ownership, and has one lead role plus optional extra role
checklists from the table; workstreams never own overlapping files. Split work across a
stack boundary, such as API and UI, into separate workstreams only when the parent can
write the contract between them before dispatch and each side is substantial enough to
run in parallel. Otherwise one workstream carries both role checklists.

Each workstream has at most one thread at a time. Send follow-up work in its area,
including review fixes and defects the parent finds, to that thread as a continued
assignment, using the host reference's mechanism for continuing a thread. A continued
assignment restates the ownership and states every spec, design, or scope revision since
the thread's last brief.

Resolve a workstream's route once, when its thread starts, from its lead role and the
hardest tier expected in its area. Continued assignments keep the thread's model and
effort. The parent never changes a workstream's route on its own; a different route
requires an explicit user choice. When a thread struggles, continue it, take the fix
over under the delegation threshold, or ask the user.

Retire a thread once parent verification passes and no follow-up is pending. Retire it
as `blocked` when its unfinished work is abandoned, or when the run ends blocked or
interrupted with that work unfinished. A thread waiting on a user decision stays active.
Leave context compaction to the host default and record it when observed. When work
later arrives in a retired workstream's area, continue the retired thread if the host
can still reach it; otherwise start a new thread seeded with a parent-written summary of
the workstream's state, and record it as a new thread for that workstream.

Before starting a thread, inspect worker state and capacity. Reuse threads only through
workstreams and reviewer rechecks, keeping each thread's route, role guidance, and
ownership. When capacity is exhausted, sequence the work or keep it under the delegation
threshold instead of repeatedly spawning or silently changing settings; follow the host
reference after a capacity rejection. A failed dispatch never counts as running.

Use one concise handoff containing:

- Workstream, lead role and any extra checklists, interaction, repository and
  instruction paths, and the requested model/effort.
- Outcome, exact file ownership or advisory-only scope, dependencies, and exclusions.
- Relevant user/repository constraints and OpenSpec artifacts, tasks, and scenarios.
- Expected verification and the compact reply contract below; return the instruction
  path actually read. Report effective settings only when the runtime supplies them.
- Worker boundaries: no recursive delegation, shared-log writes, or OpenSpec updates.

Require a handoff status: **draft** (unverified or blocked), **locally checked** (named
checks passed, integration remains), or **ready for integration** (assigned acceptance
checks passed and no known blocker). For executable changes, run the smallest relevant
authorized compile or contract check before claiming readiness. If execution is outside
the assignment or unavailable, return a draft with the unrun command and reason.
Include exact results and remaining gaps; none of these labels replaces parent verification.
For test assignments, confirm fixture/API signatures against an analogous working test
and complete the smallest authorized compile or representative setup check before the
combined acceptance selection. If the worker cannot execute it, keep the handoff at draft
and name a parent-owned integration check before selecting the combined suite.

Advisory workers that cannot access required evidence should promptly report the exact
gap, continue useful accessible inspection, and state the resulting coverage limit. The
parent resolves access or keeps the review at draft; missing evidence does not require
unrelated project execution.

Coordinate writes through assignment ownership and dependencies. Before integration,
reconcile changed paths with assigned ownership and resolve any unowned or conflicting change.

## Worker communication

Supply a compact reply contract in each assignment. Target about 200 words for a
routine completion; this is a soft target, not truncation or a reason to omit
material findings, failed/unrun checks, coverage gaps, blockers, or required decisions.
Retain the existing readiness statuses and the instruction path actually read.

- Implementers: outcome, changed paths, exact checks/results, material gaps/concerns,
  next action/owner, and evidence references.
- Reviewers: scoped verdict, actionable findings with stable IDs and locations,
  coverage gaps or failed/unrun checks, and evidence references.
- Planners/advisors: recommendation, consequential tradeoff, unresolved decisions,
  verification needs, and supporting references.

When substantial detail is expected, assign a worker-owned evidence path separately
from application-file ownership. Keep full matrices, reproduction details, logs, and
captures there; return the real path and relevant section. Small complete inline
results do not need a report file. If artifact storage is unavailable or outside
ownership, preserve necessary evidence inline and report the limitation; do not
invent a saved report or discard required detail to meet the target.

Send interim messages to the parent only for blockers, ownership conflicts, required
decisions, or consequential changes to an earlier result. Deliver completion once;
do not send the same final handoff through both a message and the final response.
On follow-up, report changed results and still-open finding IDs/blockers, referring
to earlier evidence instead of repeating the original report.

Prefer completion notifications or bounded waits for native workers. Inspect state
when it informs a next action; do not repeatedly request progress or dump unchanged
messages/logs. Read returned digests first, then retrieve the specific artifacts and
evidence needed for acceptance. A short reply never replaces parent verification.

## Review and integrate

For substantial plans, select external cross-review before implementation; for substantial
integrated changes, select it before completion. This includes UI/API/data contracts,
consequential architecture, auth, migrations/data integrity, deployment, and measured
performance risk. Honor explicit requests and opt-outs, skip small low-risk edits,
and record the reason. Planning-only authorization permits only the planning checkpoint.

Before preparing or launching a selected external review, read
`clanker-cross-review.md` from the same source/reference layout as the specialists.
It owns packet preparation, routing to the launcher named in `routing/host.json`,
source-change reconciliation, and the one-automatic-recheck limit; the reviewer's
prerequisites are in the host reference. The external reviewer supplements native
review and tests; it does not authorize implementation or deployment.

Assign browser/test acceptance separately with an owner and evidence status; do not
ask a static reviewer to certify a live check. Browser QA and other long acceptance work
run in a worker that owns the browser state and records evidence, not in the parent,
unless the user explicitly directs the parent to do it; log that the parent kept it at
the user's direction. The parent keeps the evidence states and verifies the worker's
evidence before marking acceptance tasks complete. Split large reviews by coherent
responsibility; the parent retains the full acceptance checklist and unresolved checks,
including work outside a bounded recheck.

For native correctness review, reuse `clanker-code-review`, preferring the current
repository's copy; otherwise resolve the installed skill as described above.
Supply the verified base and task-owned committed, staged, unstaged, and untracked
scope; follow that skill's evidence collection procedure. Exclude unrelated user changes
and record anything unreviewed.

A native reviewer performs its own single automatic recheck in the same thread. Its
brief contains the finding IDs, the fix diff, and a request to check the changed lines
for regressions. Start a fresh native review of the affected scope instead when the
spec or design changed after the first review, or the change grew beyond the reviewed
scope. External cross-review rechecks keep their fresh-session behavior.

For UI visual acceptance, select `clanker-ui-ux-reviewer` with `visual-review` routing
after integration. Supply application/startup details, routes, acceptance context,
viewports, and artifact locations. Require rendered evidence; unavailable access means
incomplete coverage. Assign browser ownership and recheck affected states after fixes.

Verify worker findings and integrated results against actual artifacts and proportionate
checks. Keep failed or unrun required validation visible and affected tasks incomplete.
Before accepting inventory, bytecode, hash, or smoke checks that consume build or staging
output, wait for the owned producer to finish successfully and record the artifact or
revision consumed.
Use `clanker-refactor-review` only for requested improvement proposals and
`clanker-sync-your-docs` when the task affects durable guidance.

## Keep a concise run log

Use `<repo>/.clanker/YYYY-MM-DD-orchestration-nation.md` with the local start date.
Create a distinct run ID from a timezone-bearing timestamp plus a known session ID
or checked ordinal. Retain the run ID and original file on resume or across midnight.

Append complete, run-attributed timestamped blocks; never rewrite a whole-file snapshot.
Preserve other runs. Take every block's and ledger row's time, with its timezone offset,
from the host clock at write time, for example `date` in the same append command; never
estimate, reconstruct, or copy a time from an earlier entry. Read relevant entries on resume or when reconciling uncertain
state, rather than rereading the growing log before every append. Record:

- At start: workspace, branch, request, session when known, OpenSpec context, the
  orchestration host and its preference source, parent settings, complexity/risk
  rationale, and any no-delegation decision.
- Before dispatch: assignment ID, workstream, role/interaction, instruction paths,
  ownership, concise rationale, and the readable settings line below. Capture routing
  evidence, as described in the dispatch procedure, when a workstream's thread starts;
  a continued assignment refers to that evidence.
- On meaningful changes: actual dispatch outcome, observed settings or unknown,
  verification results, review dispositions/waivers, blockers, and snapshot reloads.
  Use readable timestamped blocks that name the run and assignment, status, owned paths,
  evidence/check, and next owner.
- At completion: completed, blocked, or interrupted outcome and remaining checks.
  State task completion separately from native review, external review, and runtime
  acceptance; mark each evidence state complete, partial, pending, or excluded, and
  explain exclusions without treating them as waivers.
  Reconcile pending events from observed state after an abrupt interruption.

Every worker dispatch and external review block opens with one readable settings line
built from the resolver JSON or the launcher's `report.json`, never retyped from
memory, for example
`Model: haiku · Reasoning: Adaptive/straightforward → medium · Observed: unknown`.
It states the requested model and reasoning effort, including fixed or Adaptive mode and
the assessed tier, and the observed model and effort only when the runtime or reviewer
report supplies them. Unreported observed values read `unknown`; never infer them from
the request or a model's self-description. The block also states the host, and the
provider and execution kind (`native` or `external`) from the resolver output. An
external review block names the reviewer provider and links its `report.json`.

Also append one CSV row per orchestration event to `<repo>/.clanker/orchestration-ledger.csv`
for spreadsheet analysis. Create it with a header row when it is absent; never rewrite
or reorder existing rows. If the columns change, write to a new versioned file, such as
`orchestration-ledger-v2.csv`, rather than mixing headers. The columns, in order:

`time`, `run`, `workstream`, `event`, `thread`, `lead_role`, `route`, `detail`,
`followup_kind`, `defect_source`, `observed_model`, `observed_effort`, `final_context`,
`outcome`

Each row's `event` is one of:

- `start`: the run started; `detail` summarizes the request.
- `assign-new`: a workstream's thread started; `route` is the resolved model, effort,
  and tier.
- `assign-continued`: a follow-up went to an existing thread. `followup_kind` is
  `defect` when it fixes a finding, with what found it in `defect_source`, or `scope`
  when a requirement or the scope changed.
- `parent-kept`: the parent kept build work; `detail` gives the reason.
- `retire`: a thread retired; the row carries the outcome and observed columns, and
  `detail` notes any compaction observed in the thread.

Leave columns that do not apply empty. Append with Python's `csv` writer, which quotes
commas and quotes, and take the time from the clock in the same command. Pass all 13
values after the path, using `""` for empty ones:

```text
python3 -c 'import csv,datetime,os,sys;a=sys.argv;assert len(a)==15,"need path + 13 values";new=not os.path.exists(a[1]);f=open(a[1],"a",newline="");w=csv.writer(f);new and w.writerow("time run workstream event thread lead_role route detail followup_kind defect_source observed_model observed_effort final_context outcome".split());w.writerow([datetime.datetime.now().astimezone().isoformat(timespec="seconds")]+a[2:]);f.close()' <repo>/.clanker/orchestration-ledger.csv <run> <workstream> <event> <thread> <lead_role> <route> <detail> <followup_kind> <defect_source> <observed_model> <observed_effort> <final_context> <outcome>
```

A `retire` row records the workstream's outcome, decided from the parent's own
verification evidence, never from worker readiness claims:

- `first-pass`: accepted without fixes; `scope` follow-ups are not fixes.
- `revised`: accepted after fixes by the same thread.
- `rerouted`: the parent took over a fix, or the user directed the work to a different
  route; name the replacement in `detail`.
- `blocked`: not completed, including work a worker called ready that failed required
  parent verification, abandoned work, and work left unfinished when the run ended
  blocked or interrupted.

Name what found the defects in `defect_source`, such as native review, external review,
parent verification, or acceptance. Take `observed_model`, `observed_effort`, and
`final_context` from runtime evidence as the host reference describes, or write
`unknown`. Follow-up counts come from the workstream's `assign-continued` rows, not from
the retire row. Work after a retire row gets new rows; earlier rows stay unchanged.

Reuse generated routing JSON and link review reports instead of restating their fields
in narrative. Keep entries free of secrets, raw private payloads, and hidden reasoning.
Disclose failed saves and do not claim a log exists when writing failed.

Tell the user what completed, what was verified, remaining limitations, and the saved
log path. Do not infer successful execution from a routing preview or worker claim.
