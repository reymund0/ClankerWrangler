---
name: sync-ai-context-docs
description: Keep CLAUDE.md and docs/conventions/ in sync with meaningful repository changes. Run this skill at the end of a task to review what changed and update documentation if needed. Use this whenever you've completed a task involving architecture changes, new conventions, utilities, build/test workflows, auth/data flow changes, or persistence patterns. The skill will analyze the git diff, determine if updates are needed, propose specific changes, and ask for approval before modifying files.
---

# Sync AI Context Docs

At the end of a task, review the changes you made and update repository documentation to keep AI guidance in sync with the codebase.

## When to Use

Run this skill **after completing a task** if the work involved:

- Architecture or module structure changes
- New coding conventions or patterns
- New shared utilities, abstractions, or services
- Build, test, run command changes
- Authentication, data flow, or persistence changes
- Updated testing strategies or test patterns
- Changes to always-on AI guidance (CLAUDE.md scope)

**Do NOT run this skill for:**

- One-off feature logic (even if it's a new feature)
- Temporary experiments or proof-of-concepts
- Formatting-only edits or whitespace changes
- Bug fixes that don't affect patterns or conventions
- Refactors that preserve existing conventions

## How It Works

1. **Analyze the changes**: Read git diff to see what code changed
2. **Identify scope**: Determine if changes are meaningful enough to warrant documentation updates
3. **Search existing docs**: Check CLAUDE.md and docs/conventions/ to see where guidance should go and avoid duplication
4. **Propose updates**: List specific files and changes needed
5. **Request approval**: Show what will change and ask before updating
6. **Update docs**: Make the changes, preserving existing style and structure
7. **Report impact**: Summarize what was updated and why

## Process

### Step 1: Analyze Changes

Read the git diff to understand what changed:

```bash
git diff main...HEAD --no-ext-diff
```

Identify the nature of changes:
- Architecture/structure (new modules, folder reorganization)
- Code patterns (new utility, new service pattern, new abstraction)
- Workflow (new commands, new build steps, new testing approach)
- Data/persistence (new entities, new data flow, new constraints)
- Cross-cutting (new shared utilities, new middleware, new events)

### Step 2: Determine Scope

Check if changes are **meaningful** (require documentation):

**Meaningful changes:**
- New module or feature architecture
- New coding pattern or convention (e.g., "always use X pattern for Y")
- New utility that will be reused (e.g., a base component, a shared extension)
- New build/test command or workflow
- New data flow or persistence constraint
- Changes to testing strategy or test patterns
- Changes to authentication, authorization, or security patterns

**Not meaningful:**
- Single-use feature logic
- One-off bug fix
- Refactor that preserves conventions
- Temporary experimental code
- Pure formatting or style cleanup

If the changes are not meaningful, **report that no documentation updates are needed** and stop.

### Step 3: Search Existing Documentation

Before proposing new docs, check what exists:

- Read `CLAUDE.md` (main AI guidance)
- Read `AGENTS.md` and `.windsurf/rules/media-ranker.md` (symlinked mirrors of CLAUDE.md)
- Scan `docs/conventions/` folder for related topics
- Check if there's already guidance that needs updating (not creating new)

Rules:
- `CLAUDE.md` is the authoritative always-on guidance
- `docs/conventions/` holds deeper, optional topic-specific guidance
- **Update existing docs first**; only propose new files if truly needed
- Avoid duplicate guidance across files

### Step 4: Propose Updates

For each meaningful change, propose:

1. **File to update**: CLAUDE.md or docs/conventions/specific-topic.md
2. **Section/area**: Where in the file the guidance goes
3. **Current state**: What's there now (if anything)
4. **Proposed change**: What to add, update, or clarify
5. **Reason**: Why this matters

Format your proposal clearly so the user can review before approving.

### Step 5: Request Approval

For each proposed update:

```
File: CLAUDE.md (or docs/conventions/topic.md)
Section: [name]
Reason: [brief explanation]
Current text:
[existing text, if any]

Proposed text:
[new or updated text]
```

If proposing a **new documentation file**, always ask for approval and explain:
- What file you want to create
- Why existing docs are insufficient
- How it fits into the docs structure

### Step 6: Update Docs

After approval, make the updates:

- Preserve existing style, formatting, and structure
- Keep CLAUDE.md under ~500 lines; point to docs/conventions/ for deep dives
- Use the same tone and language as existing docs
- Avoid duplication (don't repeat info that's already in another file)
- Update the table of contents if the file has one

### Step 7: Report Impact

Summarize for the user:

```
Documentation impact:

Files changed:
- CLAUDE.md: [what was updated, briefly]
- docs/conventions/xyz.md: [what was updated, briefly]

Reason for updates:
[explain why these changes affect AI guidance]

Summary:
[1-2 sentences on what changed and why it matters for future AI work]
```

If no updates were needed, report:

```
No documentation updates needed.

Reason: These changes are [one-off feature logic / bug fix / refactor that preserves conventions / etc.]
```

## Example Scenarios

### Scenario 1: New Module Pattern (Meaningful)

**Change**: You created a new feature module with a specific structure (Data/Entities, Data/Views, Services, Controllers).

**Action**: Update `CLAUDE.md` "Repo Layout" section to document the new module structure and conventions. Also check `docs/conventions/backend-conventions.md` to see if module-level patterns need clarification.

**Result**: Propose updates to CLAUDE.md and possibly docs/conventions/backend-conventions.md with examples of the pattern.

### Scenario 2: Bug Fix (Not Meaningful)

**Change**: You fixed a null reference exception in a service.

**Action**: Check if the fix teaches any new pattern or convention. If not, skip documentation updates.

**Result**: Report "No documentation updates needed — this is a one-off bug fix that doesn't affect patterns."

### Scenario 3: New Shared Utility (Meaningful)

**Change**: You created `Shared/Extensions/StringExtensions.cs` with utility methods that will be reused across modules.

**Action**: Update `CLAUDE.md` or `docs/conventions/backend-conventions.md` to note this shared utility and when to use it. This guides future work.

**Result**: Propose adding a reference to the utility in backend conventions docs.

### Scenario 4: New Testing Pattern (Meaningful)

**Change**: You added a new test helper (`TestBuilder` class) that simplifies writing integration tests.

**Action**: Check `docs/conventions/backend-testing.md`. If it exists, update with the new pattern. If it doesn't, propose creating it.

**Result**: Update existing testing docs or ask approval to create new testing convention file.

## Notes

- Be conservative: if you're unsure whether a change is meaningful, **ask the user** rather than updating docs.
- Don't update unrelated docs during this process — focus only on impacts from this task's changes.
- Remember: the goal is to keep AI guidance in sync with the codebase, so future work can learn from your decisions.
