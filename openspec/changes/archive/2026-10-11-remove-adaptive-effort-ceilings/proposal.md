# Proposal

## Why

Adaptive profiles already let users choose the effort for Straightforward, Involved, and Demanding work. A separate ceiling makes those values misleading by reducing the requested effort after the tier mapping, while adding another control and inheritance rule to understand.

## What Changes

- Adaptive requests the selected model profile's mapped effort for the assessed tier directly. Preserve the existing tier assessment, consequential-risk floor, Fixed reasoning, route precedence, and runtime capability gates.
- **BREAKING:** Remove route/session `max_effort`, profile `default_ceiling`, and effective-route/decision `ceiling` and `ceiling_source` fields. Retired preference fields are rejected by existing strict validation; do not tolerate, strip, convert, or automatically remove them from supplied configurations.
- Remove ceiling controls, profile columns, route summaries, worked-example clamping, preview steps, and ceiling-specific logging guidance.
- Preserve the exact existing tier mappings. In particular, bundled Luna Demanding now requests `max` rather than being capped at `xhigh`.
- Advance the routing policy from version 4 to 5 across policy data, helpers, editor build compatibility metadata, and fixtures. Preserve the existing rejection of obsolete snapshots and mismatched assets.
- Update shipped configuration examples, guidance, and focused tests. Add no ceiling migration workflow, compatibility layer, dependency, or installer cleanup of user preferences.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `orchestration-routing-policy`: Direct Adaptive tier resolution, strict ceiling-field removal, and current-policy snapshot behavior.
- `orchestration-routing-editor`: Ceiling-free route controls, three-column tier profiles, examples, and preview explanations.
- `local-model-discovery`: Model-specific effort controls apply to the three Adaptive tiers and Fixed reasoning, with no ceiling selector.
- `orchestration-run-log`: Record mapped/requested effort and provenance without ceiling effects.
- `claude-cross-review`: Resolve Adaptive review effort directly from the selected profile while retaining explicit overrides and preflight.

## Impact

Touches `subagents/scripts/routing_policy.py`, bundled routing data/examples, `routing-editor/src/`, editor service/build compatibility constants, related routing/launcher/installer fixtures, and current routing guidance. Existing specs explicitly require ceilings and must change with the implementation; historical archived changes remain historical records.

Wrangler replaces the installed bundle but preserves `~/.clanker/orchestration-routing.json`. Every existing custom Adaptive profile requires `default_ceiling` under policy 4 and rejects it under policy 5, so configuration owners must coordinate a cutover: pause routing, retain their original file for rollback, deploy the new bundle, remove retired fields manually, then start a new run. Hand-editing the keys preserves customizations; the existing Reset action instead prepares an empty draft that replaces all overrides only after explicit Save. Installers will not rewrite user preferences. Preference/API schema numbering remains 1, following the existing policy-version compatibility boundary.

The log delta also preserves the handoff additions from `tighten-orchestration-handoffs`, which was independently archived and synchronized during implementation. The merged delta has been checked against the resulting main requirement. This ceiling-removal change still requires its own separately authorized sync/archive; it does not edit that other change.
