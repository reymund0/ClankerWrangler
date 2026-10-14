# Design

## Context

See `proposal.md` for motivation and the three delta specs for behavior. The source routing policy currently advertises thirteen native roles and `_validate_bundle_document` requires thirteen entries. The coordinator names all thirteen, while `routing-editor/src/specialists.ts` independently suggests roles by activity. Code review already uses a separate shared skill; the source package contains twelve native specialist instruction files plus Claude cross-review guidance.

Both installers copy source Markdown into `references/` without pruning removed source files. Their existing standalone-specialist migration iterates current source filenames, so deleting a source file also stops its old standalone directory from being migrated. Existing backup handling already preserves custom content, chooses collision suffixes, and checks permitted paths. Installer tests exercise actual PowerShell and Bash installers against temporary roots and preserve unrelated notes and preference bytes.

Policy version 5 is repeated in `subagents/routing/policy.json`, the Python resolver, the editor service, the Node launcher, and the tracked static `routing-editor/public/compatibility.json`. The launcher checks asset metadata; its build command runs TypeScript and Vite without generating the manifest. Vite copies the public manifest into `dist`, so the source manifest must be updated before rebuilding. Current helpers reject mismatched snapshots and assets. Preferences and the editor API use schema 1. `App.tsx` re-exports the editor from `RoutingWorkspace.tsx`. No active OpenSpec changes existed when this change was scaffolded.

## Goals / Non-Goals

**Goals:**

- Make the ten-role catalog consistent across instructions, routing, editor choices, and fresh or upgraded installations.
- Preserve recoverable custom content when retired installed entries leave active discovery/reference locations.
- Retain strict input validation and make the catalog cutover explicit through policy version 6.
- Keep parent product/documentation ownership and supplied design handoffs clear without losing independent rendered review.

**Non-Goals:**

- No replacement profiles, generalized profile lifecycle framework, model/effort changes, or new dependencies.
- No preference migration, automated field stripping, Claude Design integration, or external model invocation.
- No rewriting historical logs, archived OpenSpec changes, or historical design boards. Production editor assets are rebuilt from current source rather than patched by hand.
- No live installation, global preference edit, main-spec synchronization, or archival during proposal creation. Later implementation acceptance uses isolated destinations; deploying to real agent roots remains a separate authorized action.

## Decisions

### 1. Retire the profiles completely and retain explicit ownership

Remove the three Markdown files and their coordinator/catalog/editor entries. Product outcomes, scope, acceptance criteria, and routine documentation stay with the parent. Supplied Claude Design handoffs become design context for the parent and UI implementer; missing material decisions go back to the user. Keep the existing UI/UX reviewer and its live-versus-static evidence boundaries. Keep `clanker-sync-your-docs` and the separate code/refactor review skills.

Hiding editor rows alone would leave dispatchable roles and installed guidance. Remapping retired names to architecture, UI, or QA would hide a changed responsibility. Full retirement avoids both inconsistencies without introducing a new specialist.

### 2. Use policy 6 with strict retired-ID rejection

Update the catalog and its validation to the exact ten active IDs. Existing preference and request validators already derive supported roles from the bundle; retain their field-specific rejection instead of ignoring removed entries. Keep preference/API schema 1 and existing precedence, Adaptive mappings, Fixed effort, risk floors, capability checks, and ceiling-field rejection.

Advance all policy constants and the static public compatibility manifest together to 6, then rebuild and verify that the copied build manifest also contains 6. Reject policy-5 and earlier snapshots with the existing new-run message, without mutating snapshots. Keeping policy 5 would make the same version identify different supported catalogs and allow replay of retired profiles. An automatic migration would rewrite owner-managed inputs and expand this bounded removal.

### 3. Extend existing backup behavior for exact retirement targets

Use the installers' existing path validation and collision-safe backup conventions. Before writing the replacement orchestration bundle for a root, preflight its references directory, all present retirement targets, and their backup parents with component-wise checks from that agent root. Reuse `Assert-NoReparsePath` and `assert_safe_bundle_path` rather than lexical containment alone. Check the `skills`, bundle, and `references` ancestors; a regular retired file under a linked references directory is unsafe. Retired references must be regular files and retired standalone entries must be ordinary directories; reject unexpected types and linked/reparse entries, including standalone symlinks or junctions, without following or moving their targets.

After the complete replacement bundle has been successfully written, move present `references/<retired-id>.md` files and old `skills/<retired-id>/` directories into `<agent-root>/backups/orchestration-nation/`. Reference backups use `<retired-id>.md`, then `<retired-id>-2.md`, `<retired-id>-3.md`, and so on. Standalone directory backups retain `<retired-id>`, then `<retired-id>-2`, `<retired-id>-3`, and so on. Both installers use these literal names, preserve earlier occupied paths, and select the first unused suffix. Preserve exact reference bytes and full standalone directory content.

Migration must include retired standalone IDs explicitly rather than relying only on the remaining source filenames. Current-role standalone migration continues unchanged, including its existing handling of linked standalone entries. The stricter rejection applies intentionally to the three new retirement targets, where component-wise checks avoid relocating unverified references or links; it does not expand into a rewrite of retained-role migration. Handle only the three known retired references; do not sweep the references directory or delete unmatched files. If there are no retired entries, do not create retirement backups. Repeat installation must create no extra retirement backup once the entries are gone.

Keep the existing abort-on-first-error installer behavior: a preflight or move failure exits nonzero and stops later entries, later steps, and later agent roots. Preserve the failing entry, earlier backups, and already completed package writes; no automatic rollback is promised. Preflight runs before orchestration-bundle writes, not before every existing installer action, so earlier shared-skill writes may already have occurred. A move failure can leave the current root on the new bundle with unfinished retirement or rules copying, and a failure in a later root can leave earlier roots upgraded. Report the failing path and completed moves; after the owner fixes the cause, a rerun completes the remaining work without duplicating successful backups. Global two-root preflight or a transactional installer redesign is outside this change. Wholesale directory replacement would erase unrelated notes, while deletion would lose custom guidance.

The explicitly chosen agent root may itself be a link, preserving existing installation behavior. The boundary checks still reject every linked component below that root, including `skills`, `references`, retirement entries and backup parents.

### 4. Keep the editor driven by the active API catalog

Remove the retired names from activity suggestions and verify that the matrix, inspector, activity lists, and preview selectors contain only active roles. Configured exceptions remain available only for retained roles. An invalid saved retired-role override must report its path without inventing a selectable legacy row or altering the file.

Use the existing invalid-preference and explicit replacement/Reset-then-Save behavior. Validation currently reports the first invalid field, and invalid saved preferences expose no usable document. Selective correction therefore means a hand edit outside the editor, followed by Reload; list all three retired IDs in both `agents` and `interactions.<activity>.specialists` so the owner can remove them in one pass. Preserve other settings and obtain the latest loaded revision before any subsequent Save. Reset prepares a whole-document draft and only a separate Save replaces the file, so it cannot selectively preserve unrelated overrides. The separate Claude row and all existing route controls remain intact.

## Risks / Trade-offs

- Saved retired-role overrides block new routing -> give field-specific errors and document explicit owner correction; installation never edits preferences.
- Replacing helpers during an active run invalidates its old snapshot for later assignments -> deploy at an owner-selected safe point and create a fresh run after the upgrade; already running workers are not automatically stopped.
- Customized retired instructions would be lost by deletion -> move them into recoverable, collision-safe backups and test exact bytes/content in both installers.
- Unsafe paths or partial installation can prevent cleanup -> preflight source ancestors and entry types, abort on the first error, retain completed work, document possible mixed-root versions, and complete retirement through an owner-corrected rerun.
- Mixed helper/editor versions prevent startup -> bump resolver, policy data, Python service, launcher, fixtures, and the static public compatibility manifest together; rebuild and verify both built and development startup boundaries.
- Isolating preferences does not isolate Run Wrangler -> do not activate that control during rendered acceptance; exercise installation only through the dedicated temporary-root installer fixtures.
- The current main spec's reference count omits the extra Claude guidance -> explicitly distinguish nine remaining native references, one Claude reference, and the separately installed code-review skill.

## Migration Plan

1. Implement source removal, policy/editor compatibility updates, installer retirement handling, guidance, and focused checks as one coherent source change. No new dependencies are needed.
2. Update the static public manifest and build compatible editor assets. Validate fresh installs, upgrades containing all retired entries, literal backup names/collisions, repeated installs, linked ancestors and retired standalone entries, unexpected types, and failed moves using temporary agent roots. Verify preferences and unrelated files byte-for-byte, first-error exit codes, later-root nonprocessing, and recovery on rerun; record already completed root/package state without claiming rollback.
3. Before a separately authorized live upgrade, the owner selects a safe point, retains the previous complete bundle/assets for rollback, and explicitly removes any retired role keys from a valid current preference document. Existing policy-5 ceiling-field cutover rules still apply independently; this change does not repair or strip those fields.
4. Install the complete policy-6 package and matching assets; inspect reported backup destinations and start a new run/snapshot. Current supported-role preferences need no role-related edit. Do not invoke Claude or Claude Design as installation acceptance.
5. For rollback, restore the prior complete package with matching assets and restore owner-retained preferences if the owner changed them. Restore retired custom guidance from its reported backup if needed, preserving backup history, then start a run matching that helper version. Do not reuse a mismatched snapshot.

## Verification

Focused acceptance covers exact catalog membership; each retired ID rejected in requests, agent defaults, and interaction overrides; unchanged retained-role resolution; policy-5 snapshot rejection; editor invalid-load/preview/save preservation; fresh/upgrade/repeat installer behavior, exact naming, custom content, linked source ancestors/standalone entries, unexpected types, fail-fast partial states and successful reruns; and the active ten-row native matrix with its separate Claude row.

Use existing Python routing and installer tests, `python -m unittest discover -s routing-editor/tests -p 'test_routing_*.py'` for the editor service/integration family, the launcher checks, and the affected App, routePresentation, and discovery Vitest suites. Update current-version fixtures, including the installer fixture manifest, while retaining deliberately obsolete fixtures used for rejection tests. Build with the existing root `npm run build` and verify both public and copied `dist` manifests contain policy 6. Inspect the worker matrix and selectors in both themes and a narrow viewport with isolated preferences; do not click Run Wrangler. `--global-config-dir` isolates preferences only. Dedicated installer fixtures supply explicit temporary agent destinations; no test needs a paid model call, real installation, or real preference modification.
