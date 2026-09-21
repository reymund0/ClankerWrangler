## Why

Orchestration Nation currently relies on Codex workers for planning, implementation, and review. Add an independent Claude Code review for substantial work so the user can use their existing Claude subscription to challenge plans and integrated changes while Codex retains ownership of decisions and delivery.

## What Changes

- Add scope-based Claude cross-review at two checkpoints: substantial OpenSpec plans before implementation, and integrated substantial features before completion. Skip small, low-risk edits unless requested; honor explicit opt-outs.
- Default all Claude cross-reviews to the pinned `claude-opus-5` model, preserving explicit per-review overrides and adaptive effort without changing persistent Claude configuration.
- Select Claude reasoning effort for each review from its complexity and risk: low for explicitly requested mechanical checks, medium for routine bounded reviews, and high for consequential or complex reviews. Honor user overrides, reassess rechecks, and log the reason.
- Keep Codex as the only supported orchestration host for this integration. Preserve the user's selected parent model and existing Sol/Terra worker defaults; Claude is an external reviewer, not a replacement parent or native Codex subagent.
- Reuse the same specialist instruction files available to native workers as explicitly selected review guidance, preserving Claude's read-only role and recording role paths in the review evidence.
- Add bundled review guidance with plan and implementation modes and a bounded Claude Code CLI launcher. Keep one visible orchestration skill.
- Preserve subscription authentication, verify runtime capabilities, restrict reviewer tools to reading, and prevent nested delegation or application edits.
- Provide an explicit review manifest covering the selected OpenSpec artifacts, baseline, relevant committed/uncommitted/new files, and verification evidence. Detect changes to the review target while a review is running.
- Save a structured review report and link it from the existing daily run log. Codex verifies findings and records dispositions; failed, stale, or incomplete reviews never count as approval.
- Extend both existing installers to distribute the supporting launcher and references without installing Claude, changing authentication, or changing model configuration.

## Capabilities

### New Capabilities

- `claude-cross-review`: Codex-driven selection, invocation, evidence, reconciliation, and packaging of subscription-authenticated Claude Code plan and implementation reviews.

### Modified Capabilities

None. Main `openspec/specs/` currently has no published capabilities. This change builds on the implemented, unarchived `orchestration-nation` change without copying or modifying that change's delta specifications.

## Impact

- Coordinator and specialist sources under `subagents/`, new supporting launcher/tests, README usage guidance, and both wrangle installers.
- Existing shared code-review guidance remains the implementation review contract; plan review uses its own criteria.
- Runtime prerequisites for the optional integration: authenticated Claude Code CLI and Python 3.10+ for a portable standard-library launcher. No new third-party Python package, SDK, API key, service, or framework is required.
- Review invocations send the selected project context to Claude through the user's configured subscription and consume its usage allowance. Invocation is limited to scope that warrants it and remains explicitly overridable.
- Claude-led orchestration, autonomous fixes by Claude, live browser/visual review by Claude, deployments, and global installation are outside this change.
