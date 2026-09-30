## 1. Themes and shell

- [x] 1.1 Apply design tokens, fonts and system/manual themes to the existing layout; verify light/dark styling and offline fallback.
- [x] 1.2 Add shared header actions, tabs, tab error indicators, dismissible banners and anchored Wrangler details; verify retained draft, scope confirmation and save/conflict behavior.

## 2. Dedicated screens

- [x] 2.1 Move existing secondary screens into tabs then implement activity cards with specialist chips, segmented reasoning and reset controls; verify API-derived values and field errors.
- [x] 2.2 Implement effective/own profile table, customization, meters, inherited comparison and local effort example; verify CLI choices, unavailable saved values, resets and error association.
- [x] 2.3 Implement preview form and per-layer trace with authoritative winners and unknown-data fallback with resolver effort explanation; verify session overrides, risk flags, stale-response handling and no persistence/dispatch.

## 3. Worker routes

- [x] 3.1 Extract agent derivations and implement matrix/inspector and prefilled preview; verify baseline, mixed values, applicability, exceptions, sparse resets and Claude aliases with focused tests.

## 4. Acceptance

- [x] 4.1 Update App/discovery tests and add meaningful regressions; run focused editor tests and TypeScript checking.
- [x] 4.2 Complete native correctness and guarded Claude plan/implementation checkpoints; reconcile findings and record any incomplete coverage.
- [x] 4.3 Inspect all screens in both themes at desktop and 375px, keyboard focus and important interactions; record rendered evidence.
- [x] 4.4 Validate OpenSpec, inspect final diff and assess documentation impact; record completion without archiving.

## Verification evidence

- Focused App/discovery/routePresentation/draft/api suite: 71 passing; TypeScript and editor production build passed.
- Rendered review: .clanker/routing-redesign-run/visual-review/report.md (both themes,375px/desktop, keyboard and important interactions).
- Native and Claude findings reconciled in .clanker/2026-09-29-orchestration-nation.md; Claude implementation recheck completed with qualified static coverage; subsequent bounded edge fixes passed native review and focused regressions.
- Production CSP blocks external Google Fonts; system-font fallback verified. Python/API/policy unchanged. Wrangler execution and full assistive-technology audit not performed.

## 5. Revised Adaptive profiles

- [x] 5.1 Replace provider/model add controls with catalog-derived family selects, single selection and own-profile filtering.
- [x] 5.2 Render model-specific colored effort bars, preserve unavailable values, and verify responsive themes and focused regressions.

Revised profile acceptance: 71 focused tests pass; TypeScript/editor build and strict validation pass. Orchestrated test and rendered/source reviews cover family selection, saved-unavailable efforts, exact theme ramp colors and responsive layout; evidence in .clanker/routing-redesign-run/profile-visual/.

## 6. Family accordion revision

- [x] 6.1 Restore provider/model add bar and group profile row keys into shared-table family accordions with accessible counts and local expansion state.
- [x] 6.2 Verify numeric/future/Other/Claude groups, customization/error expansion, meter preservation, themes and narrow layouts with focused tests and rendered review.

Family accordion acceptance: 72 focused tests pass; TypeScript/editor production build and strict OpenSpec validation pass. Rendered and independent source reviews approved the bounded Screen 3 revision; desktop/375px, both themes, keyboard focus, counts, scope-local toggles, customization/error expansion and exact meter colors verified in .clanker/routing-redesign-run/accordion-visual/.

## 7. Editor resource organization

- [x] 7.1 Move editor scripts, integration tests and design resources under routing-editor; update root launch commands, imports, installer inputs and current docs.
- [x] 7.2 Verify relocated source/installed startup, focused editor and installer tests, build and independent review; commit the completed editor work.

Relocation acceptance: 72 UI tests, 45 Python editor/discovery/integration tests (one additional Windows symlink test skipped), 6 Node launcher tests, and 4 isolated Bash/PowerShell installer tests pass. Root npm build (including TypeScript), default Python asset discovery, strict OpenSpec validation and staged whitespace checks pass. Independent relocation review found no runtime regressions.
