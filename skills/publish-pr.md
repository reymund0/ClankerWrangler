---
name: publish-pr
description: Create GitHub pull requests with a standardized title derived from the current branch name and a concise description grounded in the actual branch diff. Use when the user asks to publish, open, or create a pull request, including draft/help-first PR preparation.
---

# Publish PR

When the user asks to publish, open, or create a pull request, follow this workflow.

## Goal

- Create a GitHub pull request.
- Build the title from the current branch name.
- Fill out the PR description based on the actual diff.

## Title Rules

1. Read the current branch name.
2. Use the segment after the first `/`.
3. Convert that segment to uppercase.
4. Format the title as `{BRANCH_SUFFIX_UPPER}: {USER_PROVIDED_TITLE}`.

Examples:

- `rc/mr-40` -> `MR-40: {USER_PROVIDED_TITLE}`
- `feature/mr-125` -> `MR-125: {USER_PROVIDED_TITLE}`

Additional rules:

- Do not guess the user-provided title suffix.
- If the user has not supplied the title suffix, ask only for that missing title suffix.
- If the branch name does not contain `/`, use the full branch name uppercased.
- If the branch suffix does not look ticket-like, still use it verbatim uppercased unless the user specifies otherwise.

## Before Creating the PR

1. Inspect the current branch name.
2. Inspect the diff against the target branch.
3. Review changed files and commit messages if helpful.
4. Check for a pull request template in the repository and follow it if present.

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

- Show the proposed title and PR description before publishing when the user asks for drafting help.
- Create the pull request when the user explicitly asks to publish/open/create it.
- If required information is missing, ask only for the missing title suffix.
