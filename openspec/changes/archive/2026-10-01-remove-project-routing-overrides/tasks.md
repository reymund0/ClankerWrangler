# Tasks

## 1. Global routing and current snapshots

- [x] 1.1 Implement global-only policy-4 snapshot creation and resolution, and remove project creation inputs; verify focused routing tests cover ignored malformed project files, five-layer precedence, profile customization, ceilings, and explicit rejection of policy-1/2/3 snapshots.
- [x] 1.2 Update coordinator and routing usage instructions to load only global preferences and document current-snapshot-only support; verify documented snapshot commands work against temporary preferences and no current dispatch instruction supplies a project config.

## 2. Editor service and launchers

- [x] 2.1 Remove project destinations and launcher flags, reject project API requests, and update compatibility metadata; verify service and launcher tests preserve global save conflicts, legacy backups, path/origin/token protection, and isolated global configuration startup.
- [x] 2.2 Update README startup and configuration examples; verify commands and help agree on global-only behavior and explain preserved but ignored project files.

## 3. Global editing interface

- [x] 3.1 Remove project selection, draft switching, inheritance branches, and preview rows; update focused UI tests to verify one global draft, five precedence layers, independent field resets, agent/activity exceptions, and configurable three-tier profiles.
- [x] 3.2 Build compatible assets and verify rendered desktop and narrow-screen editing, preview, save, reset, and error recovery; retain screenshots and confirm the global destination remains visible without a scope switcher.

## 4. Integration

- [x] 4.1 Verify editor preview matches policy-4 CLI resolution, temporary-root installation preserves existing global/project file bytes, and obsolete snapshots fail with start-new-run guidance; run strict OpenSpec validation and review the task-owned diff before marking implementation complete.
