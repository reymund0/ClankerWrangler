## Purpose

Choose the model and reasoning effort for each subagent role from one hand-edited routes file per host.

## ADDED Requirements

### Requirement: One routes file per host
Each host SHALL read role routes from one hand-edited file at `<agent-root>/clanker/routes.jsonc`, JSON with full-line `//` comments that readers ignore, containing a `host` name and a `roles` object that maps `implementor`, `reviewer`, `functional`, and `cross-review` to a model and reasoning effort. The orchestrator's own model SHALL be the user's session model and SHALL NOT be routed.

#### Scenario: Dispatch an Implementor
- **WHEN** the orchestrator starts the Implementor
- **THEN** it passes the model and effort from the `implementor` entry of that host's routes file

### Requirement: Routes edited in the repo
Each host's routes SHALL be edited in the repository at `<host>.routes.jsonc` in the repo root. Installers SHALL copy it over `<agent-root>/clanker/routes.jsonc` on every run.

#### Scenario: Reinstall after editing routes in the repo
- **WHEN** the user edits `claude.routes.jsonc` and runs the installer
- **THEN** `~/.claude/clanker/routes.jsonc` matches the edited file

### Requirement: Invalid routes block the affected role
When the routes file is missing, unreadable, not valid JSON, has a `host` that differs from the running host, or has a role entry without a non-empty string `model` and `effort`, any role that needs that entry SHALL be blocked with a message naming the file and key. The orchestrator SHALL NOT substitute a different model silently.

#### Scenario: Missing reviewer entry
- **WHEN** `routes.jsonc` has no `reviewer` entry
- **THEN** the review gate reports the missing key and does not start a Reviewer on a guessed model

### Requirement: No automatic route switching
Each dispatch SHALL use the model and effort in the routes file. The orchestrator SHALL NOT switch a role's model on its own; only the user changes a route.

#### Scenario: Implementor struggles
- **WHEN** the Implementor fails a review round
- **THEN** the orchestrator continues the same thread on the same route, handles a small fix itself, or asks the user, and does not switch the model on its own
