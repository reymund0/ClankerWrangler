---
name: clanker-orchestration-nation
description: Coordinate a bounded set of Codex specialists for software work with explicit model routing, OpenSpec continuity, and an append-only run log. Use for multi-role changes, not ordinary single-owner edits.
---

# Clanker Orchestration Nation

Coordinate only the specialists the task needs. The Codex parent owns scope,
integration, OpenSpec artifacts/task state, and the run log. Workers own bounded
assignments and return evidence; they do not recursively delegate.

Use native Codex collaboration tools. Claude Code is supported only through the
external cross-review launcher, not as the orchestration host. Do not substitute a
local Codex CLI or custom agent framework when native delegation is unavailable.

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

Resolve every assignment through that procedure using the run snapshot. Disclose the
global preference source and consequential routing limitations; do not silently
substitute settings when resolution or dispatch is blocked.

Use the returned `model` and `effort` as the native tool's model and reasoning-effort
arguments. Prefer an empty history fork with a focused assignment; a bounded history
is allowed when needed. A full-history fork inherits parent settings and must not be
used to select worker settings. Requested settings are not proof of observed settings.

## Select roles and hand off

Choose the smallest useful team. Limit concurrent assignments to three, or the runtime's
lower limit, counting Claude review; run at most one Claude review per run at a time.
Parallelize independent work and serialize changes to shared files, interfaces, browser
state, or the reviewed build. Keep useful inspection or integration work with the parent.

Before spawning, inspect worker state and available capacity. Reuse a suitable idle
worker only when its known requested model/effort matches the newly resolved route;
refresh its role, ownership, and context. Otherwise sequence the work or handle it
directly within the parent's scope. After a capacity rejection, do not repeat the same
spawn until capacity changes, and never count the rejected assignment as running.

| Role | Instruction file | Use for |
| --- | --- | --- |
| Product | `clanker-product-engineer.md` | Outcomes, scope, acceptance, edge cases |
| Architect | `clanker-architect.md` | Boundaries, interfaces, design tradeoffs |
| UX/UI | `clanker-ux-designer.md` | Flows, states, accessibility, visual direction |
| UI/UX reviewer | `clanker-ui-ux-reviewer.md` | Rendered visuals and interaction evidence |
| Backend | `clanker-backend-developer.md` | APIs, services, integrations, domain logic |
| Data | `clanker-data-engineer.md` | Contracts, queries, integrity, migrations |
| UI implementation | `clanker-ui-developer.md` | Components, forms, client state, layouts |
| QA planning | `clanker-qa-engineer.md` | Acceptance scenarios and verification strategy |
| Test engineer | `clanker-test-engineer.md` | Test implementation and execution |
| Code/security reviewer | Shared `clanker-code-review` skill | Correctness, regressions, spec coverage |
| Documentation | `clanker-documentation-writer.md` | Documentation of verified behavior |
| DevOps | `clanker-devops-engineer.md` | Build, CI, delivery, recovery |
| Performance | `clanker-performance-engineer.md` | Measured bottlenecks and improvements |

In the source checkout, specialist files sit beside this coordinator in `subagents/`;
installed packages keep them in `references/`. Shared code review is
`skills/clanker-code-review.md` in the checkout or the separate installed skill
(`../clanker-code-review/SKILL.md`). Resolve from the package actually loaded; do not
use retired skills or stale standalone specialist installations.

Read only the selected instructions, verify their names and paths, and require each
worker to read its absolute instruction path before domain work. Missing or unreadable
instructions block that assignment; independent work may continue. Specialist guidance
does not override the assignment's phase, ownership, repository rules, or authorization.

Use one concise handoff containing:

- Role/interaction, repository and instruction paths, and the requested model/effort.
- Outcome, exact file ownership or advisory-only scope, dependencies, and exclusions.
- Relevant user/repository constraints and OpenSpec artifacts, tasks, and scenarios.
- Expected verification; return changed files, evidence, blockers, and the instruction
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

## Review and integrate

For substantial plans, select Claude review before implementation; for substantial
integrated changes, select it before completion. This includes UI/API/data contracts,
consequential architecture, auth, migrations/data integrity, deployment, and measured
performance risk. Honor explicit requests and opt-outs, skip small low-risk edits,
and record the reason. Planning-only authorization permits only the planning checkpoint.

Before preparing or launching a selected Claude review, read
`clanker-claude-cross-review.md` from the same source/reference layout as the specialists.
It owns packet preparation, routing to the launcher, prerequisites, source-change
reconciliation, and the one-automatic-recheck limit. Claude supplements native review
and tests; it does not authorize implementation or deployment.

Assign browser/test acceptance separately with an owner and evidence status; do not
ask a static reviewer to certify a live check. Split large reviews by coherent
responsibility; the parent retains the full acceptance checklist and unresolved checks,
including work outside a bounded recheck.

For native correctness review, reuse `clanker-code-review`, preferring the current
repository's copy; otherwise resolve the installed skill as described above.
Supply the verified base and task-owned committed, staged, unstaged, and untracked
scope; follow that skill's evidence collection procedure. Exclude unrelated user changes
and record anything unreviewed.

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
Preserve other runs. Read relevant entries on resume or when reconciling uncertain
state, rather than rereading the growing log before every append. Record:

- At start: workspace, branch, request, session when known, OpenSpec context, parent
  settings, complexity/risk rationale, and any no-delegation decision.
- Before dispatch: assignment ID, role/interaction, instruction path, ownership, concise
  rationale, and routing evidence captured as described in the dispatch procedure.
- On meaningful changes: actual dispatch outcome, observed settings or unknown,
  verification results, review dispositions/waivers, blockers, and snapshot reloads.
  Use readable timestamped blocks that name the run and assignment, status, owned paths,
  evidence/check, and next owner.
- At completion: completed, blocked, or interrupted outcome and remaining checks.
  State task completion separately from native review, external review, and runtime
  acceptance; mark each evidence state complete, partial, pending, or excluded, and
  explain exclusions without treating them as waivers.
  Reconcile pending events from observed state after an abrupt interruption.

Reuse generated routing JSON and link review reports instead of restating their fields
in narrative. Keep entries free of secrets, raw private payloads, and hidden reasoning.
Disclose failed saves and do not claim a log exists when writing failed.

Tell the user what completed, what was verified, remaining limitations, and the saved
log path. Do not infer successful execution from a routing preview or worker claim.
