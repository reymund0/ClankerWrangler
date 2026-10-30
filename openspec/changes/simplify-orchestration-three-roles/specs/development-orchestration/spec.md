## Purpose

Coordinate software changes through one orchestrator and three subagent roles (Implementor, Reviewer, Functional Review), with a single code writer, review gates, and a handover to the user.

## ADDED Requirements

### Requirement: Three subagent roles
The orchestrator SHALL delegate only to three roles: Implementor, Reviewer, and Functional Review. It SHALL NOT dispatch any other specialist role. The orchestrator itself SHALL own scope, OpenSpec state, consolidation of reviews, small fixes, and the run log. Subagents SHALL NOT start further subagents.

#### Scenario: Role catalog
- **WHEN** the orchestrator plans delegation for a change
- **THEN** every subagent it starts is an Implementor, Reviewer, or Functional Review, and no architect, backend, data, DevOps, performance, QA, test, or UI specialist is dispatched

#### Scenario: Subagent tries to delegate
- **WHEN** an Implementor, Reviewer, or Functional Review assignment would benefit from more help
- **THEN** the subagent reports that need to the orchestrator instead of starting another subagent

### Requirement: Single code writer
A run SHALL have at most one active Implementor thread, and it SHALL be the only subagent that edits source files. Follow-up fixes SHALL go to that thread while it is reachable. Reviewer and Functional Review SHALL NOT edit source files.

#### Scenario: Review fixes return to the Implementor
- **WHEN** the code gate accepts findings that need more than a small fix
- **THEN** the orchestrator sends them to the existing Implementor thread instead of starting another writer

### Requirement: Finalized change required
The orchestrator SHALL implement only an OpenSpec change that has `tasks.md`. When it is missing, the orchestrator SHALL stop, unless the user explicitly tells it to proceed.

#### Scenario: No tasks yet
- **WHEN** the user starts orchestration and the change has no `tasks.md`
- **THEN** the orchestrator stops and points the user to the design chat

### Requirement: Orchestrator handles small fixes
The orchestrator SHALL apply a fix itself when it is small and already understood, such as a review finding needing a few lines. It SHALL delegate work that would fill its own context, including wide code reading, long test/fix loops, and browser sessions.

#### Scenario: Five-line review fix
- **WHEN** an accepted finding needs a five-line change the orchestrator already understands
- **THEN** the orchestrator applies it and records `fixed_by` as `orchestrator`

### Requirement: Worker handoff contract
Each Implementor handoff SHALL state changed paths, exact checks and results, unrun checks with reasons, and open concerns. The orchestrator SHALL verify integrated results itself and SHALL NOT mark an OpenSpec task complete from a worker claim alone.

#### Scenario: Worker claims completion with a failing check
- **WHEN** the Implementor reports done but a required check failed or did not run
- **THEN** the orchestrator keeps the affected task incomplete and records the gap

### Requirement: Functional Review
After the code gate passes, the orchestrator SHALL start Functional Review when the change can be exercised through browser automation, a CLI, or an API; otherwise it SHALL skip it and say why. Functional Review SHALL exercise the affected flows, store evidence under `<repo>/.clanker/functional/<run>/`, and report reproducible steps and coverage limits. The orchestrator SHALL triage its findings as accept, user-decision, or reject.

#### Scenario: Nothing to exercise
- **WHEN** the change has no app, CLI, or API that can be run
- **THEN** the orchestrator skips Functional Review and states the reason

#### Scenario: Running app available
- **WHEN** the code gate passes for a UI change and the app can be started
- **THEN** Functional Review exercises the affected flows and returns findings with steps, observations, and evidence paths

### Requirement: Functional fixes
Accepted Functional Review defects SHALL go to the Implementor, then through a code gate over the fixes, then a Functional Review recheck. If defects remain after two rechecks, the orchestrator SHALL list them and ask the user how to proceed.

#### Scenario: Defect fixed
- **WHEN** Functional Review finds a defect
- **THEN** the fix goes through a code gate, then Functional Review rechecks the affected flows

#### Scenario: Defects persist after two rechecks
- **WHEN** Functional Review still finds defects after the second recheck
- **THEN** the orchestrator lists the open defects and asks the user how to proceed

### Requirement: Refactor gate and handover
After Functional Review passes or is skipped, the orchestrator SHALL run one refactor-gate round and hand the thread to the user with the refactor proposal table. It SHALL NOT implement the proposals, commit, push, or open a pull request.

#### Scenario: Run completes
- **WHEN** the refactor gate has produced its proposal table
- **THEN** the orchestrator writes the final log rows and hands over with the table, without waiting for decisions on the proposals

### Requirement: Shared role guidance across hosts
The Claude and Codex hosts SHALL use the same orchestrator, role instructions, and dual-review procedure. Only native dispatch and the external reviewer SHALL differ by host.

#### Scenario: Codex-hosted run
- **WHEN** the orchestrator runs under Codex
- **THEN** it dispatches the same three roles with the same instructions and uses the Claude Code CLI for cross-review

### Requirement: Package installation
Both installers SHALL install `clanker-orchestration-nation` with its three role references and `clanker-dual-review`. Both installers SHALL also install the three role agent definitions: Claude agent files that omit edit tools from the read-only roles, and Codex custom agents under `~/.codex/agents/`. Installers SHALL delete the installed paths on a fixed list of retired names, without backups, and print each removed path.

#### Scenario: Install over the old package
- **WHEN** an installer runs where the old specialist references and worker agent are installed
- **THEN** the new package is installed, every path on the retired list is deleted, and the removed paths are printed

#### Scenario: Fresh Claude install
- **WHEN** the Claude installer runs against an empty agent root
- **THEN** it installs both skills and three agent definitions, and the Reviewer and Functional Review definitions have no Edit, Write, or NotebookEdit tools

#### Scenario: Fresh Codex install
- **WHEN** the Codex installer runs against an empty agent root
- **THEN** it installs both skills and three custom agents under `agents/`, each naming its role and pointing to its installed role file
