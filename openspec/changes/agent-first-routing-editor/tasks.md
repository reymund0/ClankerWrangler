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
- [ ] 3.2 Complete native correctness and Claude implementation reviews and reconcile concrete findings; retain freshness and verification evidence.
- [ ] 3.3 Inspect the running application at desktop and narrow viewports using isolated preferences; verify agent edit/save/reload, activity exceptions, mixed states, reset/inheritance, CLI effort controls and no runtime errors.
- [ ] 3.4 Validate and synchronize the final delta specs, verify the merge and archive this completed change; record final evidence in the orchestration log.
