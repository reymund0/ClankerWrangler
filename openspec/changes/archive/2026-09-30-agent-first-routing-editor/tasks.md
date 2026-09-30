## 1. Plan and compatibility

- [x] 1.1 Complete native architecture and guarded Claude plan review; reconcile findings against artifacts and validate this change with OpenSpec strict validation. Native review completed; Claude execution failed without coverage and the user explicitly waived the plan checkpoint; clarifications validated.
- [x] 1.2 Add sparse agent defaults, field provenance, precedence and effective agent baselines; verify focused policy tests including legacy documents, atomic reasoning and preview/dispatch parity.
- [x] 1.3 Update policy/build compatibility to version 2 while preserving frozen version-1 resolution; verify snapshot version rejection/replay and service asset compatibility tests.

## 2. Agent-first editor

- [x] 2.1 Implement agent draft helpers and primary specialist/Claude cards with CLI model and reasoning controls, mixed inherited fields and sparse field resets; verify focused draft/UI tests.
- [x] 2.2 Add optional activity customization, retained legacy interaction defaults and collapsed Adaptive controls, including visible exceptions and revealed field errors; verify scope/exception/error tests and retained save-conflict/concurrency coverage.
- [x] 2.3 Integrate updated effective data and activity preview wording without dispatch changes; verify editor tests, relevant Python integration tests and production build.

## 3. Acceptance and lifecycle

- [x] 3.1 Update routing/coordinator and user documentation to explain agent defaults, activity precedence and version compatibility; verify examples against resolver behavior and review documentation relevance.
- [x] 3.2 Complete native correctness and Claude implementation reviews and reconcile concrete findings; retain freshness and verification evidence.
- [x] 3.3 Inspect the running application at desktop and narrow viewports using isolated preferences; verify agent edit/save/reload, activity exceptions, mixed states, reset/inheritance, CLI effort controls and no runtime errors.
- [x] 3.4 Validate and synchronize the final delta specs, verify the merge and archive this completed change; record final evidence in the orchestration log.

## Final acceptance reconciliation — 2026-09-30

The routing-editor-redesign change supersedes the original card layout with a matrix/inspector and dedicated tabs; acceptance here is against that final UI, not a claim that the obsolete card layout was re-reviewed. Agent defaults, exceptions, mixed inheritance, effort restrictions and persistence remain covered by the final implementation.

- 3.2: Native and bounded Claude implementation reviews completed during the redesign. Claude recheck coverage was qualified; subsequent fixes passed native review and focused regressions. The existing plan-review waiver above remains recorded. Evidence: routing-editor-redesign tasks and local orchestration log .clanker/2026-09-29-orchestration-nation.md; Claude result .clanker/routing-redesign-run/claude-existing-session-recheck/result.json.
- 3.3: Rendered desktop/375px light/dark review exercised isolated edit/save/reset, activity exceptions, mixed states, CLI controls, error recovery and scope changes. Evidence: .clanker/routing-redesign-run/visual-review/report.md and accordion-visual/visual-report.md. No full assistive-technology audit was claimed.
- Final verification before archival: 72 UI tests, 45 Python editor/discovery/integration tests, 6 launcher tests and 4 isolated installer tests passed; one Windows symlink test skipped. Build/TypeScript passed.
- Specs are merged in dependency order: initial editor, discovery, agent defaults, then redesign. Newer Opus alias and timeout-only behavior is preserved; older card wording is superseded by the redesign.

- 3.4: All six merged main specs passed strict validation on 2026-09-30. Every selected delta requirement/scenario was verified immediately after its ordered merge; the redesign intentionally supersedes the older layout requirement. Archived with the related editor/discovery changes under the same date.
