# Design

## Context

See proposal.md for the approved scope. The coordinator already defines readiness states, cooperative write checks, and separate acceptance owners. The retrospective found inconsistent use of those contracts, not evidence for changing model routes or adding another orchestration framework.

The existing packet collector stores external guidance as `str(pathlib.Path(raw_path))`, while readiness looks up the original manifest string. Native Windows path formatting changes slash separators, causing valid captured guidance and mappings to look unavailable. The user's current edits add invocation diagnostics and progress; those edits must remain intact.

## Goals / Non-Goals

**Goals:** reinforce the existing handoff decisions at integration boundaries and fix guidance identity in local readiness with focused behavioral regressions.

**Non-Goals:** change reviewer invocation, diagnostics, model policy, retry budgets, secret filtering, manifest fields, installers, or project code; install skills or publish this change.

## Decisions

- Extend the existing coordinator and selected role references. Put fixture-specific advice in the test engineer, artifact producer/consumer ordering in DevOps, and static packet evidence in the cross-review reference. Keep shared decisions in the coordinator; avoid a new checklist subsystem or universal full-build requirement.
- Reuse the packet collector's native guidance representation for readiness lookup, aliasing only explicitly supplied guidance. Preserve raw manifest strings for coverage subjects, metadata and mapping validation. Do not globally normalize selected/context subjects or treat basename matches as available evidence.
- Retain the existing Git diff artifacts. Before claiming preservation, verify that the baseline/diff actually represents the task and identify any missing prior version. Saved historical source requires explicit scope/provenance and the existing evidence guards; this change does not create another export mechanism.
- Add a dedicated regression file so the user's existing readiness/diagnostics tests are untouched. Exercise real local preparation using temporary Git repositories, with model/preflight entry points forbidden. Test guidance aliases and mappings, and ensure missing/filtered evidence still blocks.
- Use disjoint documentation and test workers; parent owns helper/reference edits and task state. Native correctness review covers only this task's delta against the saved starting workspace, excluding concurrent diagnostics changes. Skip external Claude for this narrow local bug/guidance refinement.

## Risks / Trade-offs

- Shared launcher edits could collide with concurrent invocation work → patch only readiness lookup, save a starting copy, and verify unrelated function bodies remain unchanged by this task.
- Guidance aliasing could accidentally mark other evidence available → restrict aliases to manifest guidance and existing captured entries; keep original subjects and negative-path tests.
- Additional instruction text could inflate ordinary tasks → use existing sections, conditional checks and references; no mandatory expensive validation or synthetic timing thresholds.
- Static guidance checks do not prove future agent adherence → independently review realistic handoff decisions, without launching projects or external models.

## Migration Plan

Source changes remain reviewable in the current checkout. No global installation, commit, archive or spec synchronization is performed. Existing manifest/report formats are unchanged. The ordinary installer can distribute the source bundle after the user's concurrent diagnostics work is reconciled.
