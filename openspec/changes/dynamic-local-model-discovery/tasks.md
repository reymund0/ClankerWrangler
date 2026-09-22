## 1. Metadata adapters and service

- [x] 1.1 Implement bounded standard-library Codex and Claude metadata-only adapters, exact IDs, capability parsing, executable resolution and process cleanup; verify protocol, malformed output, timeout, shutdown and isolation failures with focused tests.
- [x] 1.2 Implement per-provider five-minute memory caching, coalesced refresh and stale last-success retention; verify concurrency, expiry and partial failures.
- [x] 1.3 Add authenticated GET /api/models and strict empty-object POST /api/models/refresh using existing boundaries; verify rejected requests never probe and config/preferences remain unchanged.

## 2. Editor and distribution

- [x] 2.1 Add separate catalog loading/refresh, provider status/provenance and reusable CLI-only model selectors for routes and session overrides; verify preservation, old-server 404 fallback and stale responses.
- [x] 2.2 Use discovered effort metadata in route/session controls while preserving unsupported saved choices and unknown metadata; verify policy intersection, alias Adaptive validation and unchanged routing semantics.
- [x] 2.3 Bundle the helper in both installers, update installed/launcher fixtures and document optional CLI discovery and refresh behavior; verify package parity.

## 3. Acceptance

- [x] 3.1 Run focused Python, component and launcher regressions, build the editor, and verify metadata-only discovery against installed CLIs.
- [x] 3.2 Complete independent native and Claude review, reconcile findings, and inspect rendered desktop/narrow model-selection and refresh states.
- [x] 3.3 Validate OpenSpec artifacts, record final evidence and limitations in the orchestration log, and confirm no preference migration or dispatch-gate change.

## 4. CLI-only selection and clearer preview (approved follow-up)

- [x] 4.1 Remove manual model entry and bundled alternatives across route/session/profile creation, preserve existing values, and rename the preview section.
- [x] 4.2 Verify loading/failure/stale catalogs, profile selection, existing values and preview behavior; update docs and review the final UI.

## 5. Updated Codex npm layout compatibility

- [x] 5.1 Support current bin/codex.exe and legacy codex/codex.exe Windows npm vendor layouts; verify both and metadata discovery with the installed updated CLI.

## 6. Adaptive profile effort dropdowns

- [x] 6.1 Replace tier and default-ceiling free text with model-specific CLI effort dropdowns; preserve validation associations and explicit unknown-metadata handling; verify component tests and build.
