## Why

The routing editor is a long scrolling page. Implement the approved four-screen design in routing-editor/docs/design/routing-editor-redesign/DESIGN.md to make inheritance and route decisions easier to inspect.

## What Changes

- Add light/dark themes, shared header actions and four persistent client-side tabs.
- Replace agent cards with a worker matrix and selected-agent inspector.
- Present activity defaults, effective/own Adaptive profiles, and explainable route previews as dedicated screens.
- Preserve every existing editor capability and the existing Python/API/persistence contracts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `orchestration-routing-editor`: Four-screen editing, route matrix/inspector, profile comparison and precedence trace.

## Impact

Only routing-editor UI, focused tests, and this change's planning artifacts. The approved organization follow-up moves editor helpers/tests/design docs into routing-editor and updates launcher, installer and documentation paths. No new dependencies, routing policy changes, preference migrations, or API additions. The previous agent-first-routing-editor change remains separately tracked.
