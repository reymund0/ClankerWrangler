## Context

See proposal.md. Preferences schema 1 currently contains interaction routes and nested specialist exceptions. The Python resolver supplies scope-aware effective routes, previews and frozen dispatch decisions; React uses debounced preview responses. Existing phase defaults differ by activity. Source files include substantial uncommitted earlier work and must be preserved.

## Goals / Non-Goals

**Goals:** Make the common agent model/reasoning choice direct, retain optional activity differences, preserve old documents and frozen runs, and keep UI and dispatch grounded in one resolver.

**Non-Goals:** Changing parent settings, automatic task assessment, new models or profile generation, changing Claude review execution, dependencies, preference migration, or automatic CLI installation.

## Decisions

1. Add optional `agents: Record<native-role-id, {model?, reasoning?}>` to schema-1 preferences. Validate known roles, nonempty routes and atomic reasoning, and reject nested specialists. Reject known Claude model IDs using the existing provider catalog; unknown exact IDs remain allowed as with existing routes and are subject to runtime capability gates. Existing interaction specialists remain activity exceptions. Claude remains `interactions.claude-review`, displayed as one cross-review agent.
2. Resolution per field: bundled interaction → global interaction → global agent → global activity specialist → project interaction → project agent → project activity specialist → explicit session override. Missing fields inherit. This preserves every old document's behavior and makes a same-scope agent choice stronger than a generic activity default. Reasoning stays atomic; a model-only edit retains explicit inherited ceilings. No new bundled agent routes are inserted.
3. Add `effective.agents[role]` with sparse merged global/project agent `route` and field `provenance`. This is the configured baseline, not the actual dispatch route. Existing `effective.interactions[activity].specialists[role]` remains authoritative for actual routing. Main fields display own draft or the effective agent baseline; absent baseline fields summarize relevant actual activities as uniform or Varies by activity. Activity details show effective values and sources, including higher-scope interaction defaults that override an inherited global agent setting. Never invent one primary activity as the truth.
4. Render one card per catalog role and a Claude card. Reuse CLI-only model and model-specific effort pickers, field errors and existing route controls. Native card uses simple model plus Adaptive/Fixed mode; Fixed reveals effort, Adaptive maximum is collapsed. Customize by activity uses the inverse of current scenario-role suggestions, retaining explicit off-scenario entries from applicable scopes. Show an activity customization/difference indicator. Existing generic interaction editors live in collapsed Advanced activity defaults; profile editor stays collapsed. Hidden field errors open their owning sections. Mixed reasoning uses an explicit unresolved display until a mode is chosen; fixed effort choices with mixed models use the policy-ordered intersection of all known reported model effort sets. Unknown/missing metadata does not erase known restrictions and adds an explicit unverified-for-some-activities note; if all are unknown, show policy-order choices as unverified. Always retain an existing saved value with an unavailable annotation when necessary. An empty known intersection offers no new effort selection and directs the user to choose a main model or activity-specific reasoning.
5. Agent edits update only `agents[role]` in the selected draft. Field reset removes only that field; agent reset removes that route and preserves all activity exceptions. Activity reset retains the existing nested-specialist semantics. Scope reset includes agents. Save/reload/dirty/conflict/error behavior remains existing. New field paths participate in error parsing/clearing. Main baseline controls update immediately from the draft, while actual effective activity values refresh from the server; stale responses cannot replace newer drafts.
6. Keep preference/API schema version 1; bump policy version and built-asset compatibility to 2 for new helpers/assets. Explicitly accept frozen policy-1 snapshots with their original semantics, reject agents in a policy-1 snapshot, require snapshot/bundle policy agreement, and report the frozen policy version in decisions. New snapshots use policy2. Unknown future versions fail closed. No rewrite of running snapshots or global/project files. Older helpers reject documents containing the unknown agents key rather than dropping preferences.
7. Preserve preview semantics and rename the visible interaction label to Activity where appropriate. Preview still selects activity/specialist, task tier and optional overrides and cannot execute models. CLI catalogs remain metadata only.

## Alternatives

UI-only fanout into every activity cell cannot represent a durable default distinct from exceptions and makes future resets ambiguous. A new schema with automatic conversion would add migration risk. The additive sparse field and policy compatibility bump keep existing state readable without silently flattening it.

## Risks / Trade-offs

- Mixed inherited settings add a visible state → label it honestly and expose concrete activity values.
- A default can be overridden → show exception/difference indicators and sources, preserve user intent rather than deleting overrides.
- New helpers could reinterpret frozen runs → pin resolution to snapshot policy and test policy1 replay.
- Existing untracked work could be overwritten → capture task-start source copies and scope worker ownership.
- UI refactor could regress async saves/errors → retain existing behavioral tests and update selectors only where layout changes.

## Verification and rollout

Focused policy tests cover precedence, sparse validation, atomic reasoning, reset equivalence, v1 documents and snapshots, version mismatch and preview/dispatch parity. UI tests cover mixed state, agent edits/reset, exceptions, scopes, advanced error recovery, CLI choices and save conflict/concurrency. Build once for rendered desktop and narrow visual checks against an isolated preferences directory. Native correctness review and guarded Claude plan/implementation reviews apply, with evidence reconciliation. Sync and archive this change after verified completion; dependency change folders remain unarchived. Rollback uses previous assets/helpers and a user-exported pre-agent document (the application does not create an automatic backup); an old helper fails closed on new agent keys, so restore a pre-agent document deliberately rather than dropping keys silently.
