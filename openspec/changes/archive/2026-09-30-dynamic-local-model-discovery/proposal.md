## Why

The editor currently uses a bundled model list and a filtered datalist that can look like a single-option selector. Installed CLI catalogs can differ from both that bundle and the active Codex session, so users need clear, current local choices without changing existing routes or weakening dispatch checks.

## What Changes

- Discover local Codex and Claude model/effort metadata without submitting prompts, creating model turns, or installing dependencies.
- Add authenticated catalog load/refresh endpoints, bounded subprocess probes, in-memory last-success caching, and explicit provider status/provenance.
- Replace model datalists with full provider-scoped selectors limited to CLI-reported model choices; derive effort choices from available metadata while preserving saved values.
- Keep Adaptive task mappings, saved routes, native runtime dispatch gates and Claude launch preflight unchanged.

## Capabilities

### New Capabilities

- `local-model-discovery`: Read-only local CLI metadata discovery, refresh/cache status, and discovery-aware model/effort selection.

### Modified Capabilities

None. This builds on the implemented but not yet archived `orchestration-routing-editor` change.

## Impact

Python editor service and a bundled discovery helper, React model/effort controls, both installers and focused tests/docs. No new runtime package, model request, credential-reading API, or persistence schema change. Local CLI metadata is required for new model choices; existing saved/inherited selections remain visible without migration. Manual model entry is not exposed.
