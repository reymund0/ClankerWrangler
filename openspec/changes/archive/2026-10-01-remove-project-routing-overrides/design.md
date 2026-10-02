# Design

## Context

See proposal.md for motivation. The resolver currently freezes global and project documents under policy 3. The Python service exposes two scopes, the Node/Python launchers accept `--project`, and React carries scope through inheritance, drafts, profiles, and preview. The completed three-tier change is not yet archived; its deltas are the effective baseline for this change.

## Goals / Non-Goals

**Goals:** Remove project configuration from the active path while retaining global customization and reproducibility within the current policy.

**Non-Goals:** No configuration framework, feature toggle, automatic project-to-global merge, file deletion, model changes, or Wrangler file-lock fix.

## Decisions

1. Use policy 4 for newly created snapshots, with only global preference documents, sources, and hashes. Remove project parameters from current snapshot creation and both editor launchers. Reject obsolete arguments rather than silently accepting settings that no longer apply. Retain policy 1–3 semantics only when resolving their frozen snapshots; add a policy-3 replay fixture before editing resolution. Reusing policy 3 would make identical version labels mean different precedence rules.
2. Simplify the existing editor store to one global destination. Keep its existing global response envelope and global scope request value to avoid unrelated API reshaping, but remove project fields and reject project requests. Retain the startup-only `--global-config-dir` for isolated testing. Keep revision conflicts, locks, atomic replacement, path guards, and exact legacy backups.
3. Remove React scope switching and project branches; render one draft and global destination. Keep global activity/agent/specialist customization and bundled inheritance. Preview shows five layers and still trusts the resolver's winning sources. Update the existing compatibility metadata alongside policy 4 so stale assets fail clearly.
4. Preserve project files without reading, migrating, merging, or deleting them. Historical snapshots are no longer supported. A feature toggle would leave the unwanted complexity in the active path.

## Risks / Trade-offs

- Old commands using `--project` fail after upgrade → update README, coordinator, routing usage, launcher help, and regression tests together.
- Existing repositories lose project-specific behavior in new runs → document global-only behavior; preserve preference files; require a new run for obsolete snapshots.
- Obsolete snapshots cannot resume after an update: reject them with start-new-run guidance; verify current-policy decisions stay unchanged.
- Earlier unarchived deltas still describe project support → synchronize/archive the completed three-tier change before this change when that operation is requested. Do not archive either as part of implementation.

## Migration Plan

Implement and verify source changes, rebuild editor assets, and verify installation against temporary roots. No preference rewrite is needed. Existing global legacy profiles retain their explicit-save conversion and backup behavior. Rollback restores the prior source and matching assets; preference files remain compatible. Policy-4 snapshots require the updated resolver and cannot be replayed by an older installation.
