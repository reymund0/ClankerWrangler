## Why

Model and reasoning choices currently live in Markdown guidance and launcher defaults, making them difficult to customize consistently. A small local React editor backed by a shared routing policy will let users control each interaction and preview model-aware Adaptive decisions before using them in Codex.

## What Changes

- Add a local React routing editor for planning/design, implementation/testing, native code review, visual/UX review, and Claude cross-review, with optional specialist overrides within each interaction.
- Persist versioned global defaults with optional project overrides. Explicit session instructions take precedence; the parent keeps its user-selected session settings.
- Support fixed effort or Adaptive effort with a ceiling. Adaptive uses assessed complexity, uncertainty, consequences, selected model, and supported effort levels. Luna can receive higher effort through an explicit model-specific policy; selecting Luna does not automatically mean max.
- Use one resolver for the editor preview and dispatch preparation, exposing inherited values, requested settings, capability limitations, and concise reasons.
- Integrate resolved settings with native worker assignments and explicit Claude launcher arguments, preserving review selection, subscription checks, read-only restrictions, and bounded rechecks.
- Preserve user preferences through Wrangler installs and record policy provenance in the existing daily run log.
- Keep model selection fixed in the first version. Recommend stronger models or independent review when warranted; automatic model switching, Claude-led orchestration, hosted accounts, and a general workflow builder are outside scope.

## Capabilities

### New Capabilities

- `orchestration-routing-policy`: Versioned configuration, precedence, interaction and role selection, model-aware effort resolution, runtime validation, and reproducible decisions.
- `orchestration-routing-editor`: Local React editing, global/project persistence, inheritance display, validation, routing previews, and accessible interaction states.

### Modified Capabilities

- `development-orchestration`: Load configurable worker routes while preserving parent settings, existing defaults, runtime boundaries, and single-skill distribution.
- `claude-cross-review`: Apply configured reviewer model and effort without changing direct-launcher defaults or review restrictions.
- `orchestration-run-log`: Record configuration provenance, assessed scenario, effort ceiling, and resolved routing rationale alongside requested and observed settings.

## Impact

A new `routing-editor/` React/TypeScript application and bundled Python routing/configuration helpers will extend the current Markdown/Python/shell repository. React, React DOM, TypeScript, and Vite are proposed editor dependencies; exact compatible versions and focused UI-test tooling will be verified during implementation. The runtime resolver and local server will use Python standard-library facilities and will not require Node for ordinary orchestration. Both Wrangler installers, coordinator/reviewer guidance, README, and focused tests will change. Preferences will live outside the installed skill bundle so reinstalling cannot overwrite them. No global agent model configuration, credentials, or application source in target projects will be modified by routing selection.
