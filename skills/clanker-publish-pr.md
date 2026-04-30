---
name: clanker-publish-pr
description: Create GitHub pull requests with a standardized title derived from the current branch name and a concise description grounded in the actual branch diff. Use when the user asks to publish, open, or create a pull request, including draft/help-first PR preparation.
---

# Clanker Publish PR

When the user asks to publish, open, or create a pull request, follow this workflow.

## Goal

- Create a GitHub pull request.
- Build the title from the current branch name.
- Fill out the PR description based on the actual diff.

## Title Rules

1. Read the current branch name.
2. Use the final segment after the last `/`.
3. Convert that segment to uppercase.
4. Format the title as `{BRANCH_SUFFIX_UPPER}: {USER_PROVIDED_TITLE}`.

Examples:

- `rc/mr-40` -> `MR-40: {USER_PROVIDED_TITLE}`
- `feature/mr-125` -> `MR-125: {USER_PROVIDED_TITLE}`
- `raymo/feature/mr-125` -> `MR-125: {USER_PROVIDED_TITLE}`

Additional rules:

- Do not guess the user-provided title suffix.
- If the user has not supplied the title suffix, ask only for that missing title suffix.
- If the branch name does not contain `/`, use the full branch name uppercased.
- If the branch suffix does not look ticket-like, still use it verbatim uppercased unless the user specifies otherwise.

## Before Creating the PR

1. Inspect the current branch name.
2. If the current branch is `main`, warn the user and cancel the skill run.
3. Inspect local working tree state with `git status --short`.
4. Do not stage or commit changes.
5. If there are uncommitted local changes, warn that they will not be included in the pushed branch unless already committed.
6. Inspect the diff against `main`.
7. Review changed files and commit messages if helpful.
8. Check for a pull request template in the repository and follow it if present.

Use these commands for the diff source:

```powershell
git diff --name-status main...HEAD
git diff main...HEAD
```

Cancel the skill run if there is no diff between `main` and `HEAD`.

## PR Description Requirements

- Ground every statement in the actual diff.
- Keep it concise and useful for reviewers.
- Do not invent tests, risks, or follow-up work.
- Mention only files, behaviors, refactors, fixes, and commands that actually changed.

When no repository template exists, use this structure:

```markdown
## Summary
- brief bullets describing the main changes

## Notes
- reviewer-relevant context, migrations, known limitations, or follow-up items only if supported by the diff
```

## Behavior

- Always show the proposed title and PR description before pushing or publishing.
- Ask for user confirmation before pushing the branch.
- Push the current branch after confirmation if it is not already pushed or if the remote branch is behind the local branch.
- Do not stage or commit local changes.
- Create the pull request only after the confirmed push succeeds.
- If required information is missing, ask only for the missing title suffix.
