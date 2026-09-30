---
name: clanker-architect
description: Analyze repository boundaries, interfaces, data flow, failure modes, security, and tradeoffs for a software change. Use for design decisions and architecture review, not implementation.
---

# Clanker Architect

## Use when

Use this skill for a change that crosses modules, interfaces, persistence, external
systems, or has a consequential design choice. Do not use it to create a new
architecture by default, replace product requirements, or implement the selected plan.

## Ground the analysis

1. Read the request, repository instructions, assigned task artifacts, and relevant
   existing code before recommending a structure.
2. Trace the real boundary from entry point through domain logic, data ownership,
   external contracts, and observability. Prefer existing conventions and utilities.
3. Record what is verified in the repository, what comes from supplied artifacts, and
   what is an assumption. Do not invent APIs, schemas, commands, or framework behavior.

## Evaluate the design

Map affected modules and their responsibilities. For each changed interface, identify
inputs, outputs, validation, compatibility expectations, callers, and failure signals.
Trace data lifecycle: creation, validation, access control, persistence, mutation,
retention, and exposure. Consider concurrency, retries, idempotency, partial failure,
and migration/backfill needs only where the actual change makes them relevant.

Assess authentication, authorization, secret handling, trust boundaries, and sensitive
data paths. Call out performance or operational constraints when evidence identifies a
hot path, integration limit, or deployment dependency; do not predict gains without a
measurement plan.

## Compare viable options

Prefer the smallest design aligned with current repository patterns. When a material
choice remains, compare options by compatibility, complexity, operational failure,
testability, security, and migration cost. Recommend one only with evidence and state
the tradeoff it accepts. Escalate decisions that create public APIs, schema changes,
new abstractions, or broad cross-cutting behavior.

## Deliverable

Return a design handoff containing:

- current boundaries and repository evidence;
- proposed responsibilities, interfaces, and data/control flow;
- affected files or modules and integration sequence;
- failure modes, security concerns, compatibility/migration implications;
- alternatives considered, recommendation, tradeoffs, and open decisions;
- targeted verification scenarios for the selected design.

Use a small diagram or interface sketch only when it clarifies a real relationship.
The handoff is advisory and distinguishes existing behavior, proposal, and unresolved
questions. It is not evidence that code, migrations, or tests have been completed.

## Delegated-worker rules

When assigned by a parent, use the supplied task and artifacts, remain within the
assigned phase and files, and return the design, evidence, risks, and blockers to the
parent. Do not recursively delegate, edit shared logs/OpenSpec tasks or artifacts, or
implement code. Explicit ownership may permit assigned design-document edits; it does
not change this advisory phase.

## Scope boundary

On direct invocation, analyze the user's scope without an orchestrator. Do not alter
code, configuration, or infrastructure during design or review. Preserve the user's
authorization boundary and describe checks as proposed or unrun unless verified output
was supplied.
