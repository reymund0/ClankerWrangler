# Design

## Context

See proposal.md for motivation and scope. The Python resolver currently uses one four-tier constant, policy version 2, and schema version 1; it already supports frozen policy-1 snapshots. Several agent-default branches test equality with the current policy version, which must not accidentally disable agent precedence for policy-2 snapshots after an upgrade. The editor shares the resolver through its existing configuration/preview/save service. Its profile table, TypeScript profile type, fallback profile, preview default, worked example, CSS columns, and compatibility metadata currently assume four tiers.

The completed review-readiness change and earlier skill simplifications are already present as uncommitted work. This proposal preserves that work and adds only planning artifacts until implementation is requested.

## Goals / Non-Goals

**Goals:** use three understandable tiers across dispatch and the existing editor, preserve user policy choices through an explicit conversion, and retain historical run reproducibility.

**Non-Goals:** numerical difficulty scoring, new structured assessment inputs, automatic classification or escalation, model switching, telemetry, dashboards, dependency changes, or an editor redesign. Do not retune model effort values as part of changing the tier vocabulary.

## Decisions

### Keep one parent judgment and one reason

Use `straightforward`, `involved`, and `demanding` as machine keys and title-case labels in the UI. The parent assesses the actual worker assignment before applying model preferences:

| Tier | Definition | Contrasting example |
| --- | --- | --- |
| Straightforward | Established approach, limited remaining decisions, direct acceptance checks. | Implement a handler using an existing pattern, or carry out a specified edit. |
| Involved | Meaningful decisions or bounded uncertainty involving related behavior. | Diagnose a reproducible bug or implement behavior with interacting edge cases. |
| Demanding | Substantial unresolved reasoning across interacting constraints or difficult correctness arguments. | Diagnose an intermittent race or design recovery with ambiguous historical data and concurrent writes. |

Guidance should assess each assignment independently, allow demanding work immediately when justified, and reassess implementation after investigation. File count, model size, missing context, unavailable tools, and the parent's overall task tier do not independently justify demanding. Missing context or access calls for resolving that blocker. Preserve the current security/data-integrity/recovery floor at the corresponding middle tier, involved; clarify assignment-specific flagging without introducing a new configurable floor or weakening existing safeguards.

Alternative considered: three scored inputs computed into a tier. Rejected for this change because those inputs still require parent judgment and would expand the request schema without evidence of benefit.

### Version policy semantics, not the whole application

Bump bundled policy to version 3 and use explicit supported-version branches: policy 1 retains its original precedence; policy 2 retains agent defaults; both retain all four old tiers, risk floors, original bundle values, and snapshot fingerprints. Policy 3 uses three tiers and retains policy-2 precedence. Derive validation and assessment rules from the snapshot's version rather than the latest global constant. Reject old tier names in new-policy requests with a clear message.

Keep the existing preference/API schema envelope at version 1. At the current-policy preference loading boundary, accept exactly one complete known tier shape per profile: legacy four keys or current three keys. Normalize legacy profiles to the current shape before creating new snapshots and returning editable editor documents. Preserve original file revision hashes for conflict detection; normalization must not mark files as saved or write them. Frozen legacy snapshots bypass conversion and validate against their embedded version. Reject unknown, incomplete, and mixed profile key sets. Existing older helpers fail closed on three-tier profiles; do not add speculative support for future versions.

Alternative considered: unversioned replacement of the tier constant. Rejected because it would invalidate historical snapshots and could break policy-2 agent precedence. A broad schema migration framework is unnecessary; reuse the existing version-aware resolver.

### Preserve chosen efforts and make retirement recoverable

Convert every legacy bundled/global/project/custom-model profile with the same mapping:

| New key | Existing value |
| --- | --- |
| straightforward | routine |
| involved | complex |
| demanding | exceptional |
| default_ceiling | default_ceiling |

Do not average efforts, lower ceilings, rename models, flatten inheritance, or touch fixed routes and specialist overrides. Mechanical has no current equivalent and is retired. In particular, a user's unusually customized mechanical value must not silently replace routine. Preserve it in unchanged source preferences until explicit save, and then in an exact backup of the original document.

Extend the existing save transaction only enough to protect this conversion: under the existing lock and revision check, create a sibling backup with a deterministic source-hash suffix before replacing a legacy document. Reuse a backup only when its bytes match; otherwise fail safely. Apply the existing pinned-root/link protections to this fixed derived path, never a browser-supplied path. Backup failure aborts replacement. Return its path after success. Normal current-format saves need no migration backup. A backup left by a subsequent failed replacement is harmless; the original preference file still wins.

The UI identifies a pending conversion without pretending it is an ordinary user edit or automatically creating own profiles. Explicit Save can complete conversion even with no additional edits. Convert only the selected saved scope; opening a project never rewrites global preferences. Existing export/reload/reset and conflict behavior remain available. Conversion details belong near the affected profiles/save state, with a brief explanation of mechanical retirement rather than a separate wizard.

### Update the existing page and preview together

Change `RoutingWorkspace.tsx`, its profile type and directly related presentation/styles to three tier fields plus the existing default ceiling. Update accessible column labels/descriptions, family-row column spans, inherited/customized states, field-error paths, fallback profiles, the worked example (involved), and Preview's selector/default (straightforward). Retain effort meters, family ordering, locally reported choices, saved-unavailable values, keyboard interaction, themes, and sparse resets.

Keep Python as the only resolver; React displays its normalized profiles and decisions. Advance the editor service/build/launcher compatibility markers together, including `routing-editor/public/compatibility.json` and `routing-editor/scripts/editor.mjs`. Update installer fixtures that assert compatibility. No model calls or automatic preference saves occur during preview, startup, or installation.

## Risks / Trade-offs

- Coarser tiers remove a separate cheap mechanical mapping → disclose that straightforward inherits routine, preserve the retired value for rollback, and leave users free to edit new mappings later. Do not claim migration preserves every old assignment's effort.
- Current-version equality checks can silently drop older agent overrides → explicit policy-1/policy-2 replay fixtures with different agent and interaction settings, legacy requests, risk floors, hashes, and expected decisions.
- In-memory conversion can confuse dirty/revision state → retain raw revision hashes and separately show pending conversion; verify no-write loading and conflict-safe saves in both scopes.
- Mismatched UI/backend assets can present invalid fields → keep compatibility checks strict and verify source and installed bundles.
- Fewer labels alone do not prove better routing → use existing logs/readiness evidence for later evaluation; this change does not add measurement infrastructure or promise equal tier usage.

## Migration Plan

Implement and test policy conversion/replay first, then service persistence and the three-tier UI against that contract. Use isolated preference directories for all migration and browser verification. Update routing guidance, examples, and documentation with the exact mapping and rollback instructions. Build only the routing editor and verify installed bundle compatibility through existing isolated installer tests.

When implementation is authorized, synchronize the changed bundle/code/assets using the existing installation path with preference preservation checks. Do not bulk-rewrite live preference files: the updated helper can consume them, and an explicit editor Save persists conversion for the chosen scope. Rollback restores the previous compatible helper/assets and, only for preferences already saved in the new form, the reported original-document backup. Existing run snapshots remain unchanged throughout. No archive, commit, publication, or paid model invocation is implied by this proposal.
