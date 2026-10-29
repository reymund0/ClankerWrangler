## Purpose

Obtain an independent, read-only review from the provider that is not hosting the run, over scoped evidence, returning structured findings with an honest status.

## ADDED Requirements

### Requirement: Opposite-provider reviewer
The launcher SHALL review with the Codex CLI for Claude-hosted runs and with the Claude Code CLI for Codex-hosted runs. Model and effort SHALL come from the host's `cross-review` route and SHALL be passed explicitly on each review.

#### Scenario: Claude-hosted code review
- **WHEN** a Claude-hosted run starts a cross-review
- **THEN** the launcher invokes the Codex CLI with the routed model and effort

### Requirement: Preflight without side effects
Before reviewing, the launcher SHALL check that the reviewer CLI is installed and logged in. It SHALL NOT install software, start a login, switch billing, or change persistent reviewer settings. A failed preflight SHALL return status `failed` naming the missing prerequisite.

#### Scenario: Reviewer CLI not logged in
- **WHEN** the reviewer CLI reports no login
- **THEN** the launcher returns `failed` with the login prerequisite and makes no model call

### Requirement: Read-only review
The reviewer SHALL run without permission to edit files, run delegated agents, or bypass the CLI's normal permissions.

#### Scenario: Reviewer attempts an edit
- **WHEN** the reviewer tries to write a repository file
- **THEN** the CLI denies the write under the launcher's read-only settings

### Requirement: Review phases
The launcher SHALL support `plan`, `implementation`, and `refactor` phases, each with its own criteria. `plan` SHALL evaluate artifacts without treating missing code as a defect; `implementation` SHALL evaluate correctness, regressions, requirement coverage, and security; `refactor` SHALL return improvement proposals rather than defects.

#### Scenario: Refactor phase
- **WHEN** the launcher runs with phase `refactor`
- **THEN** the reviewer returns proposals with locations and rationale, and the report labels them as proposals

### Requirement: Scoped evidence packet
The launcher SHALL review an explicit selection of paths and, for `implementation` and `refactor`, the committed, staged, unstaged, and untracked changes against a stated base. The reviewer MAY read other repository files for context.

#### Scenario: Diff against base with uncommitted work
- **WHEN** an implementation review is requested with a base revision and the working tree has uncommitted and untracked changes
- **THEN** the packet contains the committed diff from that base, the uncommitted diff, the untracked files, and the selected paths

### Requirement: Structured findings and honest status
The launcher SHALL validate reviewer output against a schema and write a `report.json` with a status of `clean`, `changes_requested`, `incomplete`, or `failed`, the findings, coverage limits, requested settings, and observed settings and usage when the CLI reports them. Each finding SHALL have an ID unique within the report, a severity of `blocking`, `major`, `minor`, `info`, or `proposal`, a location, and a suggested remedy. Invalid output SHALL produce `incomplete`, never `clean`.

#### Scenario: Malformed reviewer output
- **WHEN** the reviewer returns output that fails schema validation
- **THEN** the report status is `incomplete` with a diagnostic, and no findings are invented

#### Scenario: Unreported observed settings
- **WHEN** the CLI does not report the model or effort it used
- **THEN** the observed fields read `unknown`

### Requirement: Bounded run time
The launcher SHALL enforce a wall-clock limit, 45 minutes by default and configurable per invocation, and SHALL return `failed` with a timeout diagnostic when the limit is reached, leaving no reviewer process running.

#### Scenario: Review exceeds the limit
- **WHEN** the reviewer has not finished by the limit
- **THEN** the launcher stops the process and reports a timeout
