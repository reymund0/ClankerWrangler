# Proposal

## Why

The inspected MediaRanker and CardForge orchestration logs contain only two UX-designer assignments, one documentation-writer assignment, and no product-engineer assignments. UX design now uses Claude Design, while the parent already owns scope and documentation, so these profiles add maintenance and routing choices without a useful separate responsibility in this workflow.

## What Changes

- **BREAKING**: Retire `clanker-ux-designer`, `clanker-documentation-writer`, and `clanker-product-engineer` from native routing, the coordinator catalog, editor choices, and distributed instruction files, leaving ten native roles.
- Keep product outcomes, scope, acceptance criteria, and routine documentation with the parent; use supplied Claude Design handoffs for UX design and retain `clanker-ui-ux-reviewer` for rendered verification.
- **BREAKING**: Advance routing policy from version 5 to 6. Reject retired role IDs in requests and saved overrides, and reject older snapshots with the existing new-run guidance. Preserve preference/API schema 1 and existing model, effort, precedence, and validation behavior.
- Extend both installers to move only the three retired bundled references and their old standalone skill directories into consistently named, collision-safe backups during upgrades. Check source ancestors, entry types, and backup paths before replacement-bundle writes; retain strict rejection of retired links and report the first failure without rolling back completed work or processing later entries/roots.
- Update current guidance and focused routing, editor, and installer checks. Historical logs, archived changes, and design reference boards remain historical evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-orchestration`: Define the ten-role catalog, parent responsibilities and design-handoff ownership, and safe retirement of distributed specialist guidance.
- `orchestration-routing-policy`: Require the active catalog, strictly reject retired IDs, and introduce policy-6 snapshot compatibility.
- `orchestration-routing-editor`: Display only active native roles, reject retired override inputs without rewriting saved preferences, and require matching policy-6 assets.

## Impact

Source changes will affect the three specialist Markdown files, `subagents/clanker-orchestration-nation.md`, `subagents/routing/policy.json`, `subagents/scripts/routing_policy.py`, `routing-editor/src/specialists.ts`, the editor service and Node launcher policy constants, the tracked static `routing-editor/public/compatibility.json`, `wrangle.ps1`, `wrangle.sh`, routing usage guidance, and relevant tests. Vite copies that static manifest into the build; rebuilding alone does not update its version. Fresh packages contain nine native specialist references plus the retained Claude cross-review reference; code review continues to use its separate shared skill.

Owners of saved overrides for retired IDs must explicitly remove those entries before starting a policy-6 run. Installation does not modify preferences. New assignments after a helper upgrade require a fresh snapshot; running workers are not stopped by this change.

This proposal authorizes planning only. It does not remove live installed skills, rewrite global preferences, integrate or invoke Claude Design, call external models, introduce replacement profiles or dependencies, change default routing, or implement the removal.
