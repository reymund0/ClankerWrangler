# Proposal

## Why

Claude cross-review currently overrides deliberate file selection and restricts investigation to a manually assembled packet. Filename/content filters, ignored-file rejection and mandatory coverage of all context cause avoidable omissions and incomplete reviews.

## What Changes

- Default to the parent's authorized read scope: repository access plus explicit additional roots/references, with the packet identifying the reviewed change.
- Include explicitly selected files regardless of name, credential-like examples, Git ignore status or links. Preserve parent-declared exclusions.
- Separate required change evidence from optional supporting context; optional context does not determine the verdict.
- Simplify invocation to normal configured tools/permissions and session behavior; remove the forced isolation/control stack without adding permission-bypass flags.
- Convert input byte caps to warnings with optional configurable limits.
- Keep snapshots and revision attribution, remove whole-review source reservations, and report later source changes without discarding the captured review.
- Retain structured findings, model/effort/billing choices, bounded execution, owned-process cleanup and the user's diagnostics work.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-cross-review`: trusted file inclusion, investigable read scope, required/optional evidence, ordinary CLI configuration and revision-aware reports.
- `development-orchestration`: handoff authorization and integration against captured evidence without full-run review reservations.

## Impact

Implementation will touch the existing launcher, coordinator/cross-review guidance and focused Python tests. Existing manifests remain usable with the new default; optional fields describe extra read roots and truly required context. No dependencies, routing/model defaults or application code changes are planned. This followup supersedes conflicting strict-context/reservation rules from `tighten-orchestration-handoffs`, retaining its fixture, packaging and handback improvements. This request creates planning artifacts only; implementation, installation, publication and archive remain separate.
