## Why

Users think in specialist agents, but the routing editor starts with activity categories and requires repeated overrides. Make agent model/reasoning choices the primary workflow while retaining activity-specific exceptions and existing saved behavior.

## What Changes

- Present native specialists and one Claude cross-review agent as the main cards, with model and Adaptive/Fixed reasoning controls.
- Add sparse native agent defaults, optional Customize by activity, and collapsed activity defaults and Adaptive tuning.
- Preserve old preferences and phase defaults; show differing inherited values explicitly and retain activity exceptions when changing an agent default.
- Keep CLI-discovered choices, scope inheritance, draft previews, save protection, runtime gates and parent session settings intact.
- Version the updated policy/editor compatibility contract and continue resolving frozen version-1 snapshots.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `orchestration-routing-editor`: Agent-first editing, activity customization, honest inherited/mixed states and advanced controls.
- `orchestration-routing-policy`: Sparse native agent defaults with explicit precedence and backwards-compatible document/snapshot handling.

## Impact

React editor, shared Python policy, policy/compatibility metadata, routing documentation and focused tests. No new dependencies or CLI execution behavior. Completed routing-editor and discovery deltas were synchronized to main specifications as dependencies; their change folders remain unarchived. Existing preference files are not migrated on read or overwritten by installation.
