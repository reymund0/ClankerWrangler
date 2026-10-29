---
name: clanker-design-discussion
description: Discuss consequential technical architecture and system design choices through OpenSpec explore before finalizing a design or implementation tasks. Use when viable approaches need tradeoffs across performance, scalability, data, robustness, security, or maintainability.
---

# Clanker Design Discussion

Agree on a technical approach, its accepted costs, and what still needs evidence.
Keep the discussion proportional to the decisions at stake.

## Use OpenSpec explore

Resolve and invoke `openspec-explore` first (`$openspec-explore` in Codex). Preserve
its discovery, artifact handling, and authorization rules; keep its files unchanged.
If the explore skill cannot be loaded, report that dependency rather than claiming
it ran. Leave project/root selection and fallback to explore.

Carry forward existing decisions.

## Discuss the technical choices

1. **Ground the decision.** State the outcome, boundaries, constraints, and consequential
   unknowns. Separate facts, assumptions, and proposed defaults; establish workload/growth
   expectations when they influence the design.
2. **Compare credible approaches.** For each material decision, offer two or three
   viable options, including extending existing code where it fits. Compare concrete
   benefits, costs, risks, and compatibility. Explain when only one approach is
   reasonable; do not manufacture alternatives or implementation task lists.
3. **Stress the options.** Apply only the relevant lenses below. Explain how each
   concern changes an option or needs validation, rather than listing generic risks.
4. **Recommend and discuss.** Explain the preferred approach, its accepted tradeoff,
   and what would change the recommendation. Discuss components, data flow,
   failure/security behavior, and verification in short sections as useful.
5. **Agree on direction.** Resolve consequential choices with the user before treating
   the design as settled. Offer a focused investigation for blocking unknowns; label
   unrun checks as proposed.

Relevant technical lenses:

- **Performance and scale:** workload/data volume, concurrency, latency, throughput,
  resource cost, and limiting paths. Treat capacity/gains as hypotheses until measured.
- **Data:** ownership, lifecycle, consistency, integrity, transactions, queries, and
  migration compatibility.
- **Robustness and operations:** partial failure, retries, idempotency, concurrent
  changes, recovery, observability, rollout, and rollback.
- **Security:** trust boundaries, authentication/authorization, sensitive data,
  validation, and abuse paths affected by the change.
- **Maintainability:** conventions, complexity, dependencies, interfaces, testability,
  implementation cost, and reversibility.

## Review and capture

For authorized capture, follow OpenSpec explore and its resolved artifact paths.
Record choices, alternatives, rationale, accepted risks, and verification in the
design artifact; behavioral requirements in the applicable specs.

Get the user's review of the proposed design before deriving tasks or handing off to
task planning. If captured, show the actual saved artifact for that review. Use existing
authorization for follow-up work; design approval alone does not authorize implementation.

## Plan gate

After the change's proposal, design, specs, and tasks are written, review them through
`clanker-dual-review` at the `plan` gate before handing the change to implementation.

1. Start the design run:
   `python3 <clanker-dual-review dir>/scripts/clanker_log.py start --chat design --host <claude|codex>
   --change <change> --routes <agent-root>/clanker/routes.jsonc --orchestrator-model <model/effort>`.
   If it reports an invalid route, show the message to the user and stop.
2. Run `clanker-dual-review` with gate `plan`, the run ID, and the change's artifacts as scope.
   Accepted findings are fixed by this chat as artifact edits; re-run
   `openspec validate <change> --strict` after editing.
3. End the run when the gate passes (`done`), stops at its round limit (`stopped-at-limit`), or
   is blocked (`blocked`):
   `python3 <clanker-dual-review dir>/scripts/clanker_log.py finish --run <run> --outcome <outcome>`.
   Report a failed write to the user.

The change is ready for `clanker-orchestration-nation` in a new chat once the plan gate passes.
