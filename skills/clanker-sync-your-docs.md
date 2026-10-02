---
name: clanker-sync-your-docs
description: Update repository guidance after changes to architecture, shared conventions or utilities, build/test workflows, or auth/data/persistence behavior. Use when completed work changes guidance future contributors need; skip isolated fixes, formatting, and refactors that preserve existing conventions.
---

# Clanker Sync Your Docs

Keep repository guidance aligned with verified changes from the current task.

1. Inspect the task's changes, including relevant committed, staged, unstaged, and new files. Use the task's actual base branch when needed; exclude unrelated work.
2. Decide whether the changes affect durable guidance: architecture, reusable patterns, commands, or constraints future contributors need. If not, briefly report that no documentation update is needed and stop.
3. Find the repository's existing guidance and related docs, such as `AGENTS.md`, `CLAUDE.md`, `README.md`, or `docs/`. Follow its actual structure and source-of-truth rules; do not assume files exist or are mirrored. Read only the relevant sections.
4. Make the smallest update to existing documentation. Describe verified behavior, preserve the surrounding style, and avoid duplicating guidance or turning a one-off implementation choice into a universal rule. Add a file only when existing docs cannot reasonably hold the material.
5. Check the updated guidance against the implementation and commands it describes. Report the files changed and any verification limits briefly.

Respect the requested scope and existing authorization. A request to update docs authorizes the relevant edits; do not ask for the same approval again. If the user requested proposals only, provide concrete proposed text without editing. Ask before changes that expand the task or require approval under repository instructions.
