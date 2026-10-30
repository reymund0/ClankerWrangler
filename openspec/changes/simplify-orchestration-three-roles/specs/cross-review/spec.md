## Purpose

Obtain an independent, read-only review from the provider that is not hosting the run, over the scope named in the caller's handoff, returning structured findings with an honest status.

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

### Requirement: Criteria from the handoff
The launcher SHALL NOT take a phase or build in criteria. The gate and criteria SHALL come from the handoff and the Reviewer role file and criteria skill it names, read from the reviewer's own installed skills.

#### Scenario: Refactor gate handoff
- **WHEN** the handoff names the refactor gate
- **THEN** the reviewer returns proposals with severity `proposal`, following the role file

### Requirement: Shared handoff file
The launcher SHALL take the caller's handoff file by path (`--handoff`) and SHALL NOT build an evidence packet or its own scope description. Its prompt SHALL tell the reviewer to read the handoff at that path, plus the read-only note and the output schema. The reviewer SHALL read the changes against the base from the repository itself, starting from the files the handoff lists, and MAY read other repository files as needed. When the handoff path is not a readable file, the launcher SHALL return `failed` naming the path and make no model call.

#### Scenario: Diff against base with uncommitted work
- **WHEN** an implementation review is requested with a handoff naming a base and the working tree has uncommitted and untracked changes
- **THEN** the prompt points the reviewer at the handoff, and the reviewer inspects the committed diff from that base, the uncommitted diff, and the untracked files outside `.clanker/` itself

### Requirement: Structured findings and honest status
The launcher SHALL pass an output schema to the reviewer CLI, which enforces it, and write a `report.json` with a status of `clean`, `changes_requested`, `incomplete`, or `failed`, the findings, coverage limits, requested settings, and observed settings and usage when the CLI reports them. Each finding SHALL have an ID unique within the report, a severity of `blocking`, `major`, `minor`, `info`, or `proposal`, a location, and a suggested remedy. Output that is not JSON or has no findings list SHALL produce `incomplete`, never `clean`.

#### Scenario: Malformed reviewer output
- **WHEN** the reviewer returns output that is not JSON
- **THEN** the report status is `incomplete` with a diagnostic, and no findings are invented

#### Scenario: Unreported observed settings
- **WHEN** the CLI does not report the model or effort it used
- **THEN** the observed fields read `unknown`

### Requirement: Bounded run time
The launcher SHALL enforce a wall-clock limit, 45 minutes by default and configurable per invocation, and SHALL return `failed` with a timeout diagnostic when the limit is reached, leaving no reviewer process running.

#### Scenario: Review exceeds the limit
- **WHEN** the reviewer has not finished by the limit
- **THEN** the launcher stops the process and reports a timeout
