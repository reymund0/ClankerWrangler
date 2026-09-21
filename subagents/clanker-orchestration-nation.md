---
name: clanker-orchestration-nation
description: Coordinate a bounded set of Codex specialists for software work with explicit model routing, OpenSpec continuity, and an append-only run log. Use for multi-role changes, not ordinary single-owner edits.
---

# Clanker Orchestration Nation

## Purpose

Coordinate only the specialists a software task needs. Keep one parent accountable for
scope, integration, OpenSpec state, and the run log. Workers provide focused evidence;
they do not become a second orchestration layer.

This workflow is driven by Codex. If the active orchestration host is Claude Code,
report that Claude-led orchestration is not supported yet; do not recursively launch
this workflow. Installation into both clients does not imply host compatibility.

Use native collaboration delegation for Codex workers, never a custom agent framework
or a local Codex CLI workaround. The bounded Claude Code cross-review launcher below
is an explicit external-review exception. Do not invoke deprecated skills from `skills/legacy/`.

## Start and classify

1. Read the request, repository instructions, relevant code, current git state, and
   existing OpenSpec state before choosing roles.
2. Identify the target repository, branch, requested outcome, affected ownership,
   complexity, risks, and user authorization boundary.
3. Treat a documentation-only edit, localized low-risk bug fix, or one-file change as
   a likely single-owner task. Record the lightweight choice; do not manufacture a team.
4. Use OpenSpec for a meaningful feature, cross-cutting behavior, uncertain acceptance
   criteria, or an existing selected change. Resolve the actual change directory,
   artifacts, state/store, and task identifiers using installed OpenSpec workflows when
   available. Do not invent their paths, state, commands, or results.
5. If planning only was requested, preserve that boundary. If a new change is authorized,
   use the installed OpenSpec workflow to scaffold it and follow its artifact instructions.
   If the intended existing change is missing or ambiguous, report it and ask the user which change applies before making
   a competing plan or starting implementation.

## Model and effort policy

Keep the user-selected parent settings and use these worker defaults unless the user
explicitly chooses otherwise:

| Phase | Model | Typical effort |
| --- | --- | --- |
| Parent coordination | User-selected session model | User-selected session effort |
| Planning and review | `gpt-5.6-sol` | medium; high for architecture, data, security, or complex review |
| Implementation and bounded tests | `gpt-5.6-terra` | medium; high for complex logic or data/security risk |

The model selected by the user when invoking this skill remains the orchestrator,
with its selected session effort. Astra or Fable may be suggested where available;
these are optional recommendations, not prerequisites. Do not block work or request
approval merely because the user selected another parent model. This skill does not
switch the active parent model or effort. If the parent model or any effective setting
is unknown, say it is unknown. Parent choice does not guarantee worker availability:
do not silently substitute an unavailable worker model, effort, or delegation
capability, and never claim a worker ran when dispatch did not succeed.

Choose worker effort from the current task: low for mechanical work, medium for bounded
implementation or routine planning, high for unclear interfaces, complex logic, data
or security risk, and demanding review. Use xhigh or above only for an identified
reason and a supported model. Record the reason; do not escalate effort automatically.

Use native delegation with actual arguments supported by the active runtime, for example:

```text
spawn_agent({
  task_name: "backend_implementation",
  fork_turns: "none",
  model: "gpt-5.6-terra",
  reasoning_effort: "medium",
  message: "...focused assignment..."
})
```

Do not use a full-history fork when selecting model or effort: it inherits the parent
settings. `fork_turns: "none"` is preferred; a bounded history is allowed only when
the added context is necessary. State the requested and observed settings separately
in the assignment result and log.

## Role catalog and selection

Select the smallest team justified by scope, dependencies, uncertainty, and risk.
Each role has a separate instruction file with its working method and evidence
requirements. The specialist files are bundled references, not separately
discovered skills. The catalog selects the instructions to load; it does not replace
them. The existing general-purpose code-review skill remains separately installed.

| Role | Required instructions | Select when it adds distinct evidence |
| --- | --- | --- |
| Product | `clanker-product-engineer` | User outcomes, scope, acceptance criteria, and edge cases. |
| Architect | `clanker-architect` | Boundaries, interfaces, failure modes, and design tradeoffs. |
| UX/UI | `clanker-ux-designer` | User flows, interaction states, accessibility, and visual direction. |
| UI/UX reviewer | `clanker-ui-ux-reviewer` | Rendered application visuals, responsive layouts, interactions, and evidence-backed UX findings. |
| Backend | `clanker-backend-developer` | Server behavior, APIs, integration, and domain logic. |
| Database/data | `clanker-data-engineer` | Data contracts, queries, integrity, migrations, and backfills. |
| UI implementation | `clanker-ui-developer` | Components, client state, forms, and responsive behavior. |
| QA planning | `clanker-qa-engineer` | Acceptance scenarios, risk coverage, and test strategy. |
| Test engineer | `clanker-test-engineer` | Implementing and executing reliable tests. |
| Code/security reviewer | `clanker-code-review` | Correctness, security, regression, and OpenSpec coverage review. |
| Documentation writer | `clanker-documentation-writer` | User and developer documentation grounded in verified behavior. |
| DevOps engineer | `clanker-devops-engineer` | Build, CI, delivery, operations, and recovery. |
| Performance engineer | `clanker-performance-engineer` | Measured bottlenecks and verified performance changes. |

Resolve and read only the selected role instructions before dispatch:

- Source checkout: specialist files are beside this coordinator in
  `subagents/<role-name>.md`.
- Installed package: specialist files are `references/<role-name>.md` relative to
  the directory containing this coordinator's `SKILL.md`. They do not have their own
  `SKILL.md`, metadata, or skill-menu entry.
- Shared code review: use `skills/clanker-code-review.md` in this source checkout;
  elsewhere resolve the actual catalog path or the existing sibling
  `../clanker-code-review/SKILL.md` relative to the installed coordinator directory.

Use the layout of the coordinator actually loaded and verify the selected file exists
and its frontmatter name matches. Do not substitute stale standalone specialist
installations. If required instructions are missing or unreadable, report their name,
log the affected assignment as blocked, and continue only independent work. Do not
silently fall back to the catalog sentence or claim the guidance was loaded.

Put the resolved absolute instruction path in the worker assignment and instruct the
worker to read it before domain work. These files steer workers; native delegation
creates the subagent and the parent supplies its model, effort, and bounded context.
Require the result to identify the instruction file actually read and log that path.
Native planning/review phases default to Sol and implementation phases to Terra, including when one
specialty participates in both phases. Instructions must not override the assigned
phase, file ownership, repository instructions, or existing user authorization.

## Delegation rules

Use no more than three concurrent work assignments, counting an external Claude review,
subject to a lower runtime concurrency limit. Run at most one Claude review per run at a time. Delegate
only independent work that gives useful parallel evidence while the parent performs
useful coordination, inspection, or integration. Combine or sequence work that changes
the same file, schema, interface, or unsettled decision. Serialize overlapping edits.

Every assignment must include:

- the requested role, phase, model, effort, and one-sentence rationale;
- the verified absolute role-instruction path and instruction to read it before working;
- repository path, relevant instructions, request summary, and selected OpenSpec
  change/artifact paths plus task IDs and scenarios when applicable;
- in-scope outcome, excluded scope, dependencies, exact file ownership, and whether
  the worker may edit files or is advisory only;
- required verification, expected response format, and instruction to report blockers;
- instruction never to recursively delegate, modify the shared log, or update OpenSpec
  planning artifacts or task state.

Give independent implementers disjoint file ownership. The parent alone writes the
run log, resolves and updates OpenSpec planning artifacts/task state, and integrates
worker changes. A worker report is evidence, not proof of completion.

Minimal assignment shape:

```text
Read first: <absolute path to selected specialist reference or shared SKILL.md>
Role/phase: <role>; requested model/effort: <model>/<effort>; why: <brief reason>
Repo: <absolute path>; task: <summary>; OpenSpec: <change, artifacts, task IDs>
Own: <files or advisory-only>; dependencies: <known interfaces or none>
Do: <bounded outcome>; do not: <excluded scope or delegation>
Verify: <commands/scenarios>; return: loaded instruction path, changed files, evidence, blockers, observed settings.
```

For documentation, publish only verified behavior and identify evidence. QA planning
must describe unrun checks as unrun; it cannot call tests passing. For performance,
record baseline, method, comparable result, and limitations. For DevOps, retain the
user's authorization boundary and do not deploy unless expressly requested.

For visual acceptance after UI changes, select `clanker-ui-ux-reviewer` in the review
phase on Sol. Supply the running application or documented startup workflow, target
routes, design/acceptance context, viewports, and artifact locations. Require actual
rendered inspection and evidence; source-only review cannot pass visual acceptance.
Run it after the relevant UI changes are integrated and available in the target build.
Assign browser/tab ownership explicitly and serialize workers that would change the
same browser state or reviewed build. Treat unavailable visual access as incomplete
coverage; send fixes to the assigned implementer and recheck affected states afterward.

## Claude cross-review checkpoints

Read `clanker-claude-cross-review.md` from the same source/reference layout as the
specialists when selecting a Claude review. This is external reviewer guidance, not a
native Codex worker role. The parent invokes its supporting launcher directly.
Select relevant specialist instructions from the same role catalog above and include
verified paths through guidance_paths. Log the chosen roles and instruction paths;
Claude applies them as advisory criteria under its existing read-only restrictions.
The cross-review reference explains how to interpret implementation-oriented profiles.

Select an independent plan review before implementing a substantial plan, and an
implementation review after the substantial change is integrated. Substantial scope
includes UI/API/data contract changes, consequential architecture, authentication,
authorization, migrations/data integrity, deployment, or measured performance risk.
Skip small low-risk edits by default. Honor explicit requests and opt-outs and log the
reason. A planning-only request authorizes only the planning checkpoint. Do not add a
Claude call after every task or treat review as authorization to implement/deploy.

Default Claude reviews to Opus 5 (`claude-opus-5`); honor an explicit per-review
model override without changing persistent Claude configuration.

Before each Claude dispatch, use the cross-review reference's scope/risk effort policy:
low for requested mechanical checks, medium for routine bounded reviews, high for
complex or consequential reviews. Honor user overrides, pass --effort explicitly, and
log the phase, choice, and reason. Reassess effort for a recheck from its remaining
scope/risk; do not automatically inherit, lower, or raise it. Keep the existing skip
rules and one-recheck limit.

Keep the initial packet free of other reviewers' conclusions. Sol review and tests
remain applicable. Restrict Claude to a stable snapshot and read/search tools; the
launcher verifies subscription authentication and refuses API/provider overrides.
Unavailable prerequisites block the selected checkpoint, not independent work.

The parent verifies each returned finding against the actual evidence, merges
conflicting/duplicate findings, and records `accepted`, `rejected`, `deferred`, or
`needs-evidence` with reasons and locations. Assign accepted fixes to the implementer;
Claude does not edit. Recheck the source fingerprint before accepting any verdict.
A successful process can still report defects; stale, failed, partial, or missing
reports cannot approve the checkpoint. Accepted blocking findings remain unresolved
until fixed and verified or explicitly waived by the user. A waiver must be logged as
a waiver, never a pass. Allow one automatic recheck per phase after fixes or added
context; after that report remaining issues and ask for direction instead of looping.

Append selection, dispatch, report path, observed settings, outcome, reconciliation,
and any waiver to the existing run log. Neither Claude nor the launcher may write
that log or OpenSpec tasks. Preserve every attempt's report and keep incomplete
verification visible in task state and the final response.

## OpenSpec lifecycle

Follow installed OpenSpec skills and their real resolved paths/state/store when they
are available. Do not unconditionally propose, implement, synchronize, or archive a
change. Respect phase boundaries and user intent:

- Planning: clarify scope and create or revise only the requested OpenSpec artifacts.
- Implementation: use the selected change's tasks and relevant scenarios as acceptance
  evidence; the parent marks a task complete only after integrated verification.
- Completion: synchronize or archive only when the user requests it or the applicable
  OpenSpec workflow authorizes that step.

If OpenSpec is unavailable for meaningful work, say so and do not fabricate CLI output
or spec-driven completion. A tiny scoped fix may use a lightweight logged decision;
the log does not replace requirements or authorize a scope change.

## Run log

At the local run start, choose `<repo>/.clanker/YYYY-MM-DD-orchestration-nation.md` using
the local start date. Create a run ID from the timezone-bearing start timestamp plus a
known session ID, or a checked ordinal if no session ID is available. Keep the same
run ID and originally selected file when the run resumes or crosses midnight.

Create the `.clanker` directory when absent. Before every append, read the current log
if it exists. Start a distinct run for a new invocation; a continuation retains its run ID.
Append one complete run-attributed block;
never replace a loaded whole-file snapshot. Preserve other sessions and previous runs.
The parent is the sole writer. On an append failure, disclose it and do not describe a
file as saved. Never include secrets, raw private payloads, or hidden reasoning.

Append a run header first, then timestamped events before dispatch and when observed
outcomes change. Be concise, factual, and distinguish requested settings from known
effective settings. Record complexity (low, moderate, or high) and the concrete factors
behind that assessment in the initial entry and whenever it changes. Record a decision
not to delegate and unavailable capabilities.

Reusable event shape:

```markdown
## Run <run-id> — started <timestamp>
Workspace: <path> | branch: <branch> | session: <known or unavailable>
Request: <sanitized summary> | OpenSpec: <change/state or none>
Requested settings: <parent/workers> | observed settings: <known or unknown>
Complexity: <low|moderate|high> | factors: <scope, uncertainty, dependencies, risk>

### Run <run-id> / event <ordinal> / <timestamp> / <assessment|dispatch|outcome|verification|final>
Roles/skills/ownership: <roles, resolved instruction paths, and owned files>
Decision: <brief rationale or no-delegation choice>
Evidence/status: <actual command, artifact, result, failure, or unrun check>
Blockers/next step: <sanitized blocker or none>
```

For dispatch, log role, resolved instruction path, requested model/effort, ownership, and status before calling
the native tool. If it fails, append the failure without treating the worker as
running. On resume, read existing entries and reconcile a pending event from observed
state; do not assume success. Before ending when execution permits, append completed,
blocked, or interrupted status, remaining checks, and the log path supplied to the
user. An abrupt interruption may leave a running event.

## Integrate and report

Reconcile worker reports with repository evidence. Inspect integration boundaries and
run the proportionate checks authorized by the task. Keep OpenSpec tasks incomplete
when required validation failed or was not run. Assess review findings against the
actual result; they are not proof by themselves.

When an independent correctness review is warranted, use `clanker-code-review` if
available, including its OpenSpec scenario coverage and drift checks. Prefer a relevant
repository copy over an outdated installed copy. Explicitly request a working-tree-inclusive
review rather than its default branch-only scope: provide the verified baseline ref,
committed diff, `git diff HEAD`, staged diff when relevant, and an enumerated list of
this task's untracked files from `git ls-files --others --exclude-standard`. Instruct the
reviewer to read those untracked files as well as the diffs; names alone are not evidence.
Include exact task-owned paths and exclude unrelated user work. If the review cannot
cover part of that scope, record it as unreviewed rather than implying a full verdict.
Use `clanker-refactor-review` only for requested improvement proposals,
not as a mandatory second review. For meaningful documentation impact, reuse
`clanker-sync-your-docs` when applicable, preserving existing user authorization.

Tell the user what completed, what was verified, and any concrete unrun or failed
checks. Include the log path when logging succeeded. Do not fabricate agent runs,
test results, settings, performance improvements, deployments, or OpenSpec state.
