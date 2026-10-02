# Proposal

## Why

Project logs show useful reviews repeatedly ending incomplete because evidence was unreadable, filtered, or wider than the reviewer's tools and scope. Predictable launch failures and ambiguous worker handoffs also create avoidable parent rework.

## What Changes

- Add local packet preparation with coverage/readiness feedback before external execution, preserving all existing filters and authorization boundaries.
- Supply line-readable Git diff artifacts instead of embedded long JSON strings.
- Separate static review requirements from parent-owned browser/test acceptance, with optional explicit requirement-to-evidence mappings and bounded review guidance.
- Report sanitized failure categories and stages, check required writable locations before CLI/model work, and preserve unique attempts.
- Guide capacity-aware worker reuse and explicit draft/locally-checked/ready-for-integration handoffs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-cross-review`: local preparation, actionable coverage checks, readable evidence, and safe launch diagnostics.
- `development-orchestration`: scoped review acceptance and capacity-aware, verified handoffs.

## Impact

Changes are limited to the existing launcher, focused tests, coordinator/reviewer guidance, README, and OpenSpec artifacts. No new dependencies, routing changes, automatic model fallback, expanded reviewer tools, or permission bypasses. Existing manifests remain accepted; packets whose required evidence is unavailable stop earlier instead of spending a model call to report inevitable incomplete coverage.
