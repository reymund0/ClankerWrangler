## MODIFIED Requirements

### Requirement: Specialist coverage without mandatory full-team activation
The skill SHALL define architecture, UI/UX visual review, backend, data/database, UI implementation, QA planning, test implementation, code/security review, DevOps, and performance roles. It SHALL select only roles justified by the current scope, dependencies, uncertainty, and risk. The parent SHALL own product outcomes, scope, acceptance criteria, and routine documentation. The coordinator SHALL use supplied Claude Design handoffs for UX design without requiring or automatically invoking that external service, and SHALL NOT assign the retired UX designer, documentation writer, or product engineer profiles.

#### Scenario: Documentation-only change
- **WHEN** the user requests a bounded documentation update
- **THEN** the parent performs the documentation work without automatically spawning backend, data, DevOps, or performance workers or assigning a retired documentation profile

#### Scenario: Performance-sensitive deployment change
- **WHEN** the task includes deployment configuration and a measurable performance regression
- **THEN** the orchestrator considers DevOps and performance specialists, with Sol planning/review and Terra implementation as applicable

#### Scenario: Product scope remains parent-owned
- **WHEN** a change needs clarified outcomes, scope boundaries, or acceptance criteria
- **THEN** the parent resolves those decisions with the user and records the applicable OpenSpec artifacts without dispatching a product engineer

#### Scenario: Supplied UX design and rendered verification
- **WHEN** the user supplies a Claude Design handoff for a UI change
- **THEN** the parent uses that handoff as design context, assigns bounded UI implementation where justified, and retains UI/UX review for rendered and interaction evidence without dispatching a UX designer

#### Scenario: Missing design decision
- **WHEN** a material UX decision is not resolved by the user's request, supplied handoff, or existing application patterns
- **THEN** the parent asks the user to resolve that decision rather than inventing it, reactivating a retired profile, or automatically calling Claude Design

### Requirement: One discoverable orchestration package
The coordinator and nine native specialist instruction files SHALL live under root-level `subagents/`, alongside the retained Claude cross-review guidance. Both installers SHALL install the coordinator as `skills/clanker-orchestration-nation/SKILL.md` with those ten reference files in its `references/` directory. They MUST NOT install specialist instructions as separate discoverable skills or native agent definitions. Existing standalone skills, including shared code review, SHALL retain their normal installation. The three retired profiles SHALL NOT be included in a fresh package.

#### Scenario: Fresh bundled installation
- **WHEN** either installer runs against empty agent roots
- **THEN** one orchestration skill, nine active native specialist references, and the Claude cross-review reference are installed, all selected role paths resolve, and no retired reference or separate specialist SKILL.md or metadata entry is created

#### Scenario: Upgrade from standalone specialist skills
- **WHEN** earlier standalone specialist directories exist in an agent's skills folder and any retired entries pass the retirement preflight
- **THEN** after successfully writing the bundle the installer moves eligible entries into the agent root's backups/orchestration-nation directory, preserving custom content and unrelated skills; retired links are rejected, while retained-role migration keeps its existing handling of linked standalone entries

#### Scenario: Repeated installation and backup collisions
- **WHEN** the installer runs again or an earlier backup already uses a specialist's name
- **THEN** it preserves earlier backups, chooses an unused backup name for any newly migrated entry, and creates no migration backups when there are no specialist entries to retire or migrate

## ADDED Requirements

### Requirement: Recoverable retirement of installed specialist guidance
Both installers SHALL preserve custom content when backing up only retired `clanker-ux-designer`, `clanker-documentation-writer`, and `clanker-product-engineer` references and standalone directories. Source ancestors below the explicitly chosen agent root, entry types, and backup paths SHALL be validated before replacement-bundle writes. The explicitly chosen agent root MAY itself be linked. After the bundle is ready, moves SHALL use unused backup names. Failure SHALL stop installation with a nonzero exit, retaining the affected entry and completed backups.

#### Scenario: Upgrade with retired reference files
- **WHEN** an existing orchestration bundle contains any of the three retired Markdown references, including locally customized content
- **THEN** each safe regular retired reference is moved with its exact content into the agent root's backups/orchestration-nation directory and is absent from the active references directory after successful installation; reference names use <id>.md then <id>-2.md, <id>-3.md, and so on, while standalone directory names use <id> then <id>-2, <id>-3, and so on

#### Scenario: Preserve unrelated files and preferences
- **WHEN** the installation contains unrelated reference notes, other skills, saved routing preferences, and earlier retirement backups
- **THEN** those files remain unchanged while only present retired references and the existing standalone specialist migration targets are moved

#### Scenario: Repeat an already completed retirement
- **WHEN** installation repeats after all retired entries have been moved
- **THEN** no additional retirement backup is created and the active package still excludes all three retired profiles

#### Scenario: Linked owner-selected agent root
- **WHEN** either installer uses an explicitly chosen linked agent root and all retirement source and backup components below it are ordinary entries
- **THEN** installation succeeds through that chosen root, preserves recoverable retired content, and continues to reject linked descendants

#### Scenario: Unsafe or failed retirement
- **WHEN** a retirement entry, source ancestor below the chosen agent root, or backup path is linked or escapes its permitted root, has an unexpected type, or cannot be safely backed up
- **THEN** the installer refuses the unsafe or failed move, preserves that entry and earlier backups, and aborts with a nonzero exit without processing later entries, steps, or agent roots or claiming retirement succeeded

#### Scenario: Linked references ancestor
- **WHEN** the references directory or another source ancestor under the agent root is linked, even though each retired reference itself is a regular file
- **THEN** component-wise preflight rejects that path before replacement orchestration-bundle writes or retirement moves, leaving the linked target's contents untouched

#### Scenario: Linked retired standalone entry
- **WHEN** an old standalone skill for a retired role is a symlink, junction, or other reparse entry
- **THEN** retirement preflight rejects it without moving the link or accessing its target; retained-role standalone link handling remains unchanged in runs that pass retirement preflight

#### Scenario: Unexpected retirement entry type
- **WHEN** a retired reference path is a directory or a retired standalone skill path is a regular file
- **THEN** preflight rejects the unexpected type before replacement orchestration-bundle writes and preserves its content without creating a retirement backup

#### Scenario: Partial failure and recovery
- **WHEN** a backup move fails after earlier bundle writes or retirement moves have completed
- **THEN** completed writes and backups remain, later steps and roots are not processed, and the failure output identifies the affected path without claiming rollback; after the owner corrects the cause, a rerun finishes remaining retirement without duplicating successful backups
