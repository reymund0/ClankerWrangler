# Design

## Context

See `proposal.md` for motivation and the five capability deltas for the behavior contract.

The current shared resolver in `subagents/scripts/routing_policy.py` validates sparse preferences, freezes them per run, resolves field precedence, applies the consequential-risk floor, then clamps an Adaptive profile's tier effort against either route `max_effort` or profile `default_ceiling`. Effective-route and decision responses expose ceiling values and sources. Fixed reasoning already bypasses clamping and retains capability checks.

`routing-editor/src/types.ts`, `draft.ts`, and `RoutingWorkspace.tsx` carry the same fields through activity controls, agent defaults, specialist exceptions, session preview, profile rows, and explanations. Profile CSS allocates four effort columns: three tiers and a ceiling. The service, Node launcher, and public compatibility manifest each declare policy version 4. Existing snapshots and built assets already reject mismatched policy versions.

Wrangler copies the bundle and leaves global user preferences intact. Existing preference reads and saves use strict validation; there is no need to introduce another validation or persistence layer.

## Goals / Non-Goals

**Goals:** Remove the second effort-selection step through the existing validation, resolution, and editor paths; keep preview and dispatch preparation identical; keep the change reviewable without introducing a new routing abstraction.

**Non-Goals:** Ceiling migration, legacy-field tolerance or stripping, automatic user-file cleanup, alternative route-specific caps, tier remapping, monotonic tier restrictions, model switching, provider-discovery changes, dependency additions, or installer redesign. The pre-existing four-tier-to-three-tier conversion remains outside the removal scope; documents with retired ceiling keys fail validation before that conversion can accept them.

## Decisions

### 1. Remove ceiling fields from the accepted shapes

Adaptive reasoning becomes exactly `{ "mode": "adaptive" }`. An Adaptive profile contains only `tiers`, with the existing complete three-tier mapping. Remove `max_effort` and `default_ceiling` from validators' allowed fields and delete their validation/access branches. Reuse the existing unknown-field errors for every applicable preference or session route; add no dedicated legacy-field branch.

Remove the retired fields from every bundled profile and shipped configuration example. Preserve all tier efforts and exact model keys, including unknown model profiles. Keep the existing legacy-tier normalization only for documents satisfying the new allowed-field contract, and update its fixtures accordingly.

Retired fields in a submitted document remain invalid. Preserve the editor's existing explicit replacement behavior: loading an invalid file reports its field-path error and writes nothing; Reset prepares an empty draft, and a separate Save uses the loaded revision to replace all overrides. This is a user-directed replacement, not ceiling cleanup. Owners who want to keep their customizations edit only the retired keys outside this automatic validation path.

Alternative considered: accept and discard old keys on read or explicitly migrate them on save. The user rejected both. Strict removal keeps unsupported configuration visible and avoids additional code and persistence behavior.

### 2. Resolve Adaptive effort directly

Retain the current route/profile lookup and assessment floor. For Adaptive reasoning, use the selected profile's assessed-tier effort as both `proposed_effort` and `effort`, then pass that exact request into the existing capability gate. Delete the ceiling lookup, effort comparison for clamping, and capped-effort limitation. Keep Fixed reasoning and its below-recommendation diagnostic.

Remove `ceiling` and `ceiling_source` from decision and effective-route objects entirely, including Fixed responses. Retain `proposed_effort` to avoid an unrelated response-field removal; the preview can still explain the mapping without a separate cap step. Risk-floor and capability limitations remain valid.

Alternative considered: use Demanding as an implicit ceiling or lower mappings to preserve previously capped results. Either would retain a hidden second decision or alter configured values. Each tier instead requests its own exact value. Bundled Luna Demanding consequently requests `max`; other bundled tier mappings remain identical.

### 3. Extend the existing editor components

Narrow TypeScript types and simplify `reasoningFor` so Adaptive cannot produce a maximum. Remove Adaptive effort dropdowns from the shared route editor, agent inspector, and temporary preview controls; retain Fixed effort selection, mixed-model effort intersection, field resets, and sparse overrides.

Remove ceiling annotations from matrix cells, route summaries, activity defaults, provenance rows, and preview results. Profile rows expose Model, Straightforward, Involved, Demanding, and Actions. Update the CSS grid, full-width family headers, field-error associations, and responsive sizing to the three effort columns. Keep effort meters, family ordering, keyboard behavior, and unavailable saved effort display. The worked example uses the involved mapping directly; the preview explanation proceeds from assessed tier and profile mapping to requested effort and capability status.

Alternative considered: hide the controls but retain backend ceilings. That would leave invisible settings changing the requested effort and would not remove the concept.

### 4. Use the existing policy-version boundary

Advance policy version 4 to 5 in `subagents/routing/policy.json`, `subagents/scripts/routing_policy.py`, `routing-editor/scripts/routing_editor.py`, `routing-editor/scripts/editor.mjs`, and `routing-editor/public/compatibility.json`. Update current-version fixtures and move future-version rejection fixtures beyond 5. Preserve schema/API version 1 and all existing version gates; no replay or asset-compatibility branches are added.

Alternative considered: keep policy version 4 after removing the clamp. That would reuse the same identity for different resolution semantics and permit incompatible editor assets. A schema-number change adds no useful distinction beyond the existing policy gate for this bundled deployment.

### 5. Update current guidance and verification

Update `subagents/routing/usage.md` and any current routing-specific guidance to describe direct mapping, the retired-field rejection, policy version 5, and the separate user-config deployment prerequisite. Remove ceiling effects from orchestration logging and Claude effort guidance. Keep historical archived designs and old audit output intact; unrelated uses of the word ceiling are outside scope.

The earlier `tighten-orchestration-handoffs` change modifies the same `Decisions and outcomes` log requirement. It was independently archived and synchronized during implementation at `openspec/changes/archive/2026-10-11-tighten-orchestration-handoffs/`. This merged delta was checked against the resulting main spec and preserves its two added sentences and its Ownership transfer and Bounded capture or runtime acceptance scenarios. The ordering dependency is satisfied; syncing or archiving this ceiling-removal change still requires separate authorization.

Verification during implementation will use the existing policy, editor persistence, routing integration, frontend, launcher, and isolated-installer tests. Meaningful cases cover exact custom tier values, Luna Demanding `max`, supported and unsupported capability evidence, Fixed reasoning, risk floors, model-only overrides, strict retired-field rejection at every input location, absent ceiling output keys, unchanged invalid saved bytes, and policy/asset mismatch rejection. UI checks cover the three-column profile table, Adaptive versus Fixed controls, the local example, and preview explanation at desktop and 375px widths with keyboard interaction and both themes.

## Risks / Trade-offs

- Removing an active ceiling can increase requested effort, including bundled Luna Demanding from `xhigh` to `max` -> Preserve the mappings as agreed and verify the exact request; runtime support remains a dispatch prerequisite. Users choose lower effort by changing the relevant tier mapping or selecting Fixed reasoning.
- Every existing custom Adaptive profile becomes invalid on one side of the policy cutover -> Pause routing, deploy the complete new bundle, and manually remove retired fields before starting a new run; retain the owner's original file for rollback. Verify that validation identifies the field without changing the file. This is the accepted strict-break behavior, not a compatibility workflow.
- Helpers and built editor assets can be deployed with different versions -> Update existing version constants together and verify mismatched assets and version-4 snapshots remain rejected.
- Removing an effort column can disturb narrow layouts or inaccessible controls -> Verify the existing responsive workspace, family-header spans, labels, meters, and field errors after simplifying the rows.
- The worktree already contains edits to shared skills and specialist instructions -> Implementation must preserve those edits and change only routing-ceiling references where applicable.

## Migration Plan

No ceiling data migration is implemented. The repository supplies ceiling-free bundled data and examples. Policy 4 requires `default_ceiling` for every custom profile, while policy 5 rejects it, so a custom-profile document cannot be valid under both helpers. Owner removal of optional route `max_effort` alone can occur early; profile-field removal requires the coordinated cutover below.

For rollout, pause routing and retain an owner-managed copy of the original global preferences if rollback is needed. Build policy-5-compatible editor assets and deploy the complete bundle through Wrangler. Then manually remove `default_ceiling` from every profile and `max_effort` from every route in the preserved global file before starting a new policy-5 run. Keep all tier values and unrelated preferences intact. Hand-edit the keys to retain customizations; Reset followed by Save deliberately replaces the whole preference document. Existing error handling remains available if the owner has not completed the edits. Installation does not rewrite global preferences or create a ceiling-migration backup.

Rollback restores the previous complete bundle, matching editor assets, and the owner's original matching preferences, then starts a new run; policy 4 rejects ceiling-free custom profiles, and snapshots must not be replayed under another policy version. The separate spec synchronization dependency above applies when sync/archive is later authorized.

All implementation and runtime/UI checks described here are planned, not executed by this planning change.
