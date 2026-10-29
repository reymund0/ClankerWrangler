## Purpose

Run a native Reviewer and an external cross-review in parallel at the plan, code, and refactor gates, and consolidate their findings into one triaged list for the calling chat and the user.

## ADDED Requirements

### Requirement: Parallel native and external review
Every review round SHALL start the native Reviewer subagent and the external cross-review at the same time over the same scope and wait for both. The Reviewer SHALL return its findings inline and SHALL NOT write files.

#### Scenario: Code gate round
- **WHEN** the caller starts a code review round
- **THEN** the Reviewer subagent and the cross-review launcher run concurrently over the same scope, and the Reviewer's findings arrive in its reply

### Requirement: Shared review scope
The caller SHALL give both reviewers the same scope through one handoff file at `.clanker/reviews/<run>/<gate>-<round>/handoff.md`, and each reviewer's prompt SHALL only point to it. The handoff SHALL name the gate, the Reviewer role file and criteria skill, the base, the files to start from, any round-two notes, and the rule to start from those files and explore further only as needed. At the code and refactor gates this SHALL be the change's committed, staged, unstaged, and untracked work against a stated base, including work not yet committed and excluding `.clanker/`. At the plan gate it SHALL be the change's OpenSpec artifacts.

#### Scenario: Uncommitted implementation on a branch with commits
- **WHEN** the branch already has commits and this run's implementation is uncommitted
- **THEN** both reviewers receive the committed diff from the base plus the uncommitted and untracked changes

### Requirement: Three review gates
The dual review SHALL be used at three gates: `plan` (run from the design chat over OpenSpec artifacts), `code` (run from the orchestration chat over the implementation), and `refactor` (run from the orchestration chat for improvement proposals). Each gate SHALL give both reviewers criteria for that gate.

#### Scenario: Plan gate in the design chat
- **WHEN** the design chat has generated OpenSpec artifacts for a change
- **THEN** it runs the plan gate, and accepted findings become edits to those artifacts made by the design chat

#### Scenario: Refactor gate
- **WHEN** the refactor gate runs
- **THEN** the Reviewer applies the refactor-review criteria and the cross-review runs in its refactor phase

### Requirement: Consolidation and triage
The caller SHALL merge duplicate findings, mark each finding's source as `native`, `cross`, or `both`, and triage each one as `accept`, `user-decision`, or `reject`. Each reject SHALL carry a one-line reason.

#### Scenario: Both reviewers report the same defect
- **WHEN** native and cross reviews describe the same defect
- **THEN** the consolidated list has one finding with source `both`

### Requirement: Skeptical triage
The caller SHALL treat reviewer findings as claims to verify, not instructions. It SHALL `accept` only a finding that it has confirmed against the artifacts or code, that has a concrete failure, and whose fix is the smallest obvious one. Agreement between both reviewers SHALL NOT by itself justify acceptance.

#### Scenario: Both reviewers suggest the same elaborate safeguard
- **WHEN** both reviewers recommend a safeguard for a rare failure the user has not asked to handle
- **THEN** the caller does not accept it on agreement alone and applies the overengineering escalation

#### Scenario: Unconfirmed finding
- **WHEN** a finding's claimed failure cannot be confirmed against the artifacts or code
- **THEN** the caller rejects it with that reason

### Requirement: Escalate overengineering and non-obvious recommendations
The caller SHALL triage as `user-decision`, not `accept`, any finding whose fix would add a mechanism, state, a configuration option, a requirement, or a safeguard beyond the smallest obvious fix. The same SHALL apply to any finding that reveals a planning oversight or whose remedy is not obvious. For each, it SHALL tell the user what the fix would add and why it might be overengineering.

#### Scenario: Fix adds a new mechanism
- **WHEN** a finding's remedy adds retry bookkeeping, hashing, or another new mechanism
- **THEN** the caller escalates it to the user with what it would add, and does not apply it without approval

#### Scenario: Finding exposes a planning gap
- **WHEN** a finding is valid but implies a requirement the plan did not include
- **THEN** it is triaged `user-decision` and shown to the user rather than fixed silently

### Requirement: User decisions before the gate passes
At the end of each round, the caller SHALL present the `user-decision` findings and a count of accepted and rejected findings, and SHALL wait for the user's answers before the gate passes. A finding the user chooses to take SHALL be handled as accepted.

#### Scenario: Pending user decision
- **WHEN** a round produces a `user-decision` finding
- **THEN** the gate does not pass until the user answers take or skip

### Requirement: Gate passage
A plan or code gate SHALL pass only when both reviewers completed the latest round, every accepted finding is fixed and checked, and every user decision is answered. The refactor gate SHALL pass once the user's accept or skip is recorded for every proposal; accepted proposals are resolved by being listed at handover. When either reviewer failed or was incomplete, no gate SHALL pass unless the user explicitly authorizes proceeding.

#### Scenario: Refactor proposals decided
- **WHEN** the user has accepted or skipped every refactor proposal
- **THEN** the refactor gate passes without implementing the accepted proposals

#### Scenario: Cross-review preflight fails
- **WHEN** the external reviewer's CLI is missing or not logged in and the native review is clean
- **THEN** the caller reports the cross-review as incomplete with the missing prerequisite and asks the user whether to proceed

#### Scenario: Clean round
- **WHEN** both reviewers complete with no accepted or pending findings
- **THEN** the gate passes

### Requirement: Round limits
The plan and code gates SHALL run at most two rounds each. A second round SHALL review the fixes and the code they touched. When findings remain open after the second round, the caller SHALL stop with outcome `stopped-at-limit` and list them for the user, unless the user explicitly authorizes proceeding. A fix made after the second round SHALL be checked by the caller's own verification rather than a third round. The refactor gate SHALL run one round.

#### Scenario: Findings remain after round two
- **WHEN** the second code-gate round still has accepted findings open
- **THEN** the caller stops with `stopped-at-limit` and lists them for the user

#### Scenario: User takes a finding after round two
- **WHEN** the user chooses to take a `user-decision` finding raised in round two
- **THEN** the fix is applied and checked by the caller's own verification, with no third review round

### Requirement: Standalone dual-review skill
The dual review SHALL be packaged as one standalone skill that the design and orchestration skills invoke, so the procedure has a single source.

#### Scenario: Both chats use one procedure
- **WHEN** the design chat runs the plan gate and the orchestration chat runs the code gate
- **THEN** both follow the same installed dual-review skill
