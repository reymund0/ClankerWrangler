# Proposal

## Why

The user uses one global routing configuration. Project overrides add unused precedence layers, editor state, and startup options that make routing harder to understand.

## What Changes

- **BREAKING**: New runs read only global routing preferences; remove project preference inputs and `--project` from snapshot and editor commands.
- Remove the editor's scope switcher and project inheritance logic. Keep global agent defaults, activity exceptions, configurable three-tier profiles, ceilings, and temporary session overrides.
- Show five precedence layers: bundled defaults, global activity, global agent, global activity-specific specialist, and session.
- Preserve existing project files without importing or deleting them. Preserve replay of frozen policy versions 1–3.
- Update usage instructions, compatibility metadata, and focused tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `orchestration-routing-policy`: Global-only routing with current snapshots only.
- `orchestration-routing-editor`: One global editing destination and five-layer preview.

- `development-orchestration`: Global-only routing and prerequisite disclosure.

## Impact

Changes affect the Python resolver/service, Node launcher, React workspace and helpers, tests, README, and coordinator routing guidance. No dependencies are added. This follows the completed but unarchived `simplify-adaptive-reasoning-tiers` change; its three-tier behavior remains the baseline. The unrelated Wrangler file-lock failure is outside this change.
