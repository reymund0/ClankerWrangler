# Design

## Context

See proposal.md for the observed failures. The existing dependency-free launcher already filters and fingerprints a temporary packet, reserves inputs, performs subscription preflight, and writes immutable attempt reports. Extend those paths instead of creating another service or agent framework. Current skill simplifications and retirements are prior user-approved work and must be preserved.

## Goals / Non-Goals

Keep existing manifest fields and live CLI behavior compatible while detecting impossible coverage before model use. Do not change model routing, permit arbitrary shell tools, weaken filtering, infer human export approval, or automatically certify browser/test evidence.

## Decisions

- Add `--prepare-only` to the existing manifest/output operation. It uses the real snapshot pipeline and probes report/reservation write access, then releases temporary resources. It never resolves or launches Claude. Normal execution repeats preparation rather than trusting a stale preview. A successful preparation reports `prepared`, never a clean review; failures retain stage/category/action metadata.
- Optional `requirement_paths` maps every requirement string to a nonempty list drawn from selected/context/guidance paths. Optional `parent_checks` is a bounded list of `{subject, owner, status, evidence}` records, with status `pending`, `passed`, or `failed`. These are parent-supplied acceptance records, not model-covered subjects. Legacy manifests omit both fields. Do not attempt natural-language classification of requirements.
- Block unavoidable coverage gaps (filtered or missing required files without deletion evidence). Provide counts and advisory split warnings for large packets rather than an arbitrary new hard cap. Explicit exclusions do not magically satisfy required coverage.
- Write committed/staged/unstaged diff text into `_clanker_packet/diffs/`; metadata supplies paths and hashes, and the prompt tells reviewers to read them. Keep existing Git evidence fingerprint semantics and include all generated artifacts in the existing aggregate size bound.
- Prepare local filesystem and evidence before Claude metadata/auth preflight. Capture fixed diagnostic categories and action text from known errors, never raw process output. Preserve unknown failures rather than guessing. Preparation is not external-export consent; the coordinator must review the exact manifest and destination under existing authorization rules.
- Coordinator instructions supply a concise handoff status contract and inspect native worker capacity before dispatch. No platform-specific worker registry or new routing abstraction is added.

## Risks / Trade-offs

- Earlier blocking can expose existing filtered fixtures sooner: preserve filters and explain which evidence must be safely changed or assigned elsewhere; do not send incomplete packets silently.
- Added report fields/status could affect consumers: preserve existing successful execution statuses and freshness behavior; explicitly prevent preparation results from qualifying as approval.
- Preparations can become stale: repeat all checks on actual execution and retain final fingerprints/reservations.
- Runtime diagnostics may contain secrets: map recognizable cases to constant messages and retain no arbitrary excerpts.

## Migration Plan

Verify with isolated Git fixtures and mocked Claude processes, then update installed coordinator/reference/launcher files in Codex and Claude. No preference migration or new dependencies. Restore the previous source/installed files to roll back; preparation reports remain historical evidence. No paid review or source transmission is implied by local verification.
