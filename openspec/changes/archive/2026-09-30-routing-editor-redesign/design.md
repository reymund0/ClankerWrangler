## Context

The implementation source of truth is routing-editor/docs/design/routing-editor-redesign/DESIGN.md and its boards. Existing App.tsx owns all request versioning, revision-aware saves and draft state. specialistChoices and draft helpers already encode supported UI behavior.

## Goals / Non-Goals

Implement all four screens and both themes while retaining existing request and mutation behavior. No backend behavior, policy, dependency, configuration-format or build-configuration changes. The approved organization follow-up relocates editor resources and updates their references. Do not archive the preceding change.

## Decisions

- Follow the handoff sequence: tokens on current layout; shared shell/tabs; dedicated secondary screens; extracted agent derivations and matrix/inspector; migrated regression tests.
- Keep existing shared draft and error state in App; preserve mounted screen state where useful. Use native labeled controls and accessible segmented buttons with no router or component dependency.
- Extract current agent baseline/mixed/exception derivations before reusing them in both matrix and inspector, with focused helper tests.
- Derive known per-layer trace fields from existing documents. Use returned resolver provenance for authoritative winners and strike earlier overridden values. Fall back to winning-only for fields whose reconstructed value disagrees with the decision; unknown sources display raw text rather than a guessed layer.
- Derive inherited profile comparison from bundle plus global scope when editing project, excluding current-scope overrides. Retain CLI effort restrictions and saved unavailable values.
- Use CSS variables, system theme plus manual selection, supplied fonts with offline fallbacks. Matrix scrolls internally and inspector stacks below about 1100px.

## Risks / Trade-offs

- Layout changes can hide error or draft state: retain state and test cross-tab recovery, saves/conflicts and exceptions.
- Effective preview refresh is asynchronous: preserve version guards and use draft fields for immediate controls.
- Externally changed saved documents may disagree with a preview response: verify reconstructed winners against returned fields and use the honest winning-only fallback when inconsistent.
- Board data is illustrative: all model/role/activity/status values come from current responses.

## Migration Plan

No preference migration. Rebuild existing editor assets after source verification using current tooling. Revert UI changes to roll back. Do not publish or install via Wrangler during verification.

## Interaction and verification details

- Trace layers: bundled interaction, global interaction, global agent, global specialist, project interaction, project agent, project specialist, session. Reasoning is atomic. Global preview excludes all project layers; project preview uses saved global plus draft project. No native role means empty agent/specialist layers.
- Provenance strings map exactly: bundle.defaults; scope.interactions.ACTIVITY.FIELD; scope.agents.ROLE.FIELD; scope.interactions.ACTIVITY.specialists.ROLE.FIELD; session_override.FIELD. Model and reasoning winners are independent; profile provenance is separate. Unknown source text is shown without inventing a winning layer.
- Errors on agents, specialist exceptions and claude-review belong to Worker routes; Codex interaction defaults to Activity defaults; adaptive_profiles to Adaptive profiles. Global failures use the banner. Unmappable field errors remain visible. Mark erroneous matrix rows/cells and expand selected erroneous exception editors so errors remain recoverable.
- Preserve mounted screen state: selected agent, expanded exception, profile selection, preview inputs and results survive tab changes. Prefill selected applicable cell activity or first applicable activity; Claude uses claude-review with no specialist. Keep other preview fields and invalidate obsolete results.
- Use tablist/tab/tabpanel semantics with arrow navigation and accessible error text; inline resets and real row-header buttons; Wrangler Escape/focus return. Count unsaved differing leaf fields, including removals; same-value edits count zero while retaining existing save/conflict semantics.
- Meaningful state text must meet contrast requirements on actual surfaces; faint can remain decorative. Google Fonts links are explicitly requested by the handoff and are not new package dependencies; retain offline system fallback.
- Caption activity precedence as within-scope order; project layers override global layers. Profile meters use one bar per selectable model effort plus the saved unavailable value in provider effort order, with level-specific light/dark colors. The add bar retains provider selection, a locally reported model select and Customize profile. Table rows form descending numerically sorted Codex version accordions derived from profile keys, with Claude first and Other last only when needed, inside one shared-column table. Headers expose model/customized counts and aria-expanded. Own profiles or errors start expanded; new field errors reveal their section. Expansion is component-only state. Hide the example with no own row and show unknown effort honestly. Disable inherited Customize for unreported models with explanation; preserve null metadata behavior.
- Preserve loading, missing project scope and invalid config recovery; initial load failures retain a retry action even after dismissal. Test payload behavior, request-version guards, cross-tab preview state, error ownership and inherited profile resets.

## Final review decisions

- Activity-default Set here, border and reset availability consider only own model/reasoning. Reset those two fields while retaining same-scope specialist exceptions; Claude whole-route reset remains unchanged.
- Meaningful Not used, n/a and struck values use --muted rather than --faint. Verify --error on dark surfaces.
- This change modifies Editable interaction routes and inheritance, carrying forward the prior agent-first behavior while superseding cards/collapsed advanced sections. Do not archive this change before resolving the preceding change's lifecycle; no earlier artifacts are modified here.
- Keep the existing preview invalidation on draft/form changes and scope reload. Stored theme is localStorage only. Narrow headers wrap. An agent with no applicable activity has a disabled preview action and explanation.
- The existing production CSP blocks external fonts. Keep the expressly requested Google Fonts link and verify graceful system fallback in the built server; no Python header change is authorized. Do not depend on external fonts or inline styling for usable layout.
- Resolver inspection disproves a bundled-agent/specialist merge: its starting route is the bundled interaction only. Do not invent additional precedence. Current policy has one Claude interaction; future unknown interactions are outside this UI-only redesign.


## Resource organization follow-up

Keep editor-specific Python/Node helpers in routing-editor/scripts, integration tests in routing-editor/tests, and design handoffs/boards in routing-editor/docs/design. Root npm commands delegate to the relocated launcher. Shared routing policy and cross-review helpers remain in subagents/scripts. Source editor helpers import these shared modules from the checkout; installed bundles retain adjacent helpers and existing startup behavior. Wrangler installers copy editor helpers from their new source paths.
