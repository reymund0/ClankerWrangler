# Tasks

## 1. Cross-review launcher (Codex adapter)

- [x] 1.1 Skim the old launcher tests and list the 5–6 failure modes worth keeping (malformed reviewer output, timeouts, effort handling, preflight diagnostics, and similar) at the top of the new test file; verify the list exists before any launcher code is written
- [x] 1.2 Write the new launcher core in `subagents/scripts/`: manifest, evidence packet (committed diff from base plus staged, unstaged, and untracked work, plus selected paths), `plan`/`implementation`/`refactor` phases with per-phase criteria, finding schema validation, `report.json` with status and requested/observed settings and usage, and a 45-minute default timeout; verify with `python3 -m unittest` on the new core tests
- [x] 1.3 Write the Codex adapter: preflight (CLI present and logged in, with no login or billing changes), read-only invocation, and settings passed explicitly; verify with unit tests using a stubbed CLI
- [x] 1.4 Run one real `plan`-phase review against this change's artifacts with the Codex adapter; verify the `report.json` status and findings parse
- [x] 1.5 Switch both reviewers to one shared handoff file:
  - launcher: replace `--manifest` with `--handoff <path>` (phase as a flag), drop `build_packet`, `packet.md`, manifest parsing, and `PHASE_CRITERIA`, and send "Read the handoff at <path>" plus the read-only note and output schema; return `failed` before any model call when the handoff path is unreadable
  - `clanker-dual-review`: step 2 writes `.clanker/reviews/<run>/<gate>-<round>/handoff.md` (gate, role file and criteria skill, base, files to start from, round-two notes, explore only as needed, ignore `.clanker/`) and gives both reviewers only its path
  - Reviewer role file and `clanker-reviewer` agent: read the handoff, then the role file and criteria it names (by the path in the handoff, not an absolute path); the role file's reply format applies to the native Reviewer, and an output schema in the prompt overrides it
  - Verify with updated unit tests and one real `implementation`-phase review

## 2. Routes file and run log helper

- [x] 2.1 Add the `routes.jsonc` template with the `host` and `roles` keys and the two model-listing comment commands; verify a reader that drops `//` lines parses it, and that both commands print model lists when run locally
- [x] 2.2 Write `clanker_log.py`: append events to `.clanker/runs/<run>.jsonl`, replay for resume, and write the final `runs.csv` and `findings.csv` rows with the `csv` writer; verify with unit tests covering append, replay after a clean round, replay with a pending user decision, and header creation

## 3. Dual-review skill

- [x] 3.1 Add a mode to `skills/clanker-code-review.md` and `skills/clanker-refactor-review.md` for a scope the calling chat supplies: review that scope including uncommitted work and return output inline instead of writing `.clanker/refactor/*.md`; verify by reading both skills for the new mode and running one inline refactor review
- [x] 3.2 Write the Reviewer role instructions and the Claude `clanker-reviewer` agent definition without Edit, Write, or NotebookEdit; verify the frontmatter tool list
- [x] 3.3 Write the `clanker-dual-review` skill covering the parallel round, shared scope, consolidation, skeptical triage, escalation of overengineering and non-obvious fixes, user decisions, gate passage, round limits (two for plan and code, one for refactor), and run-log events; verify each dual-review spec requirement maps to a section
- [x] 3.4 Update `skills/clanker-design-discussion.md` to run the plan gate through `clanker-dual-review` after artifacts are generated and to end its run when the gate passes, and remove its "Optional specialist references" section; verify by reading the skill
- [x] 3.5 Update `wrangle.sh` and `wrangle.ps1` to install `clanker-dual-review` with the launcher and `clanker_log.py`, `routes.jsonc` only when absent, and the Claude reviewer agent; verify by installing to temporary agent roots and checking the files, and that a second install leaves an edited `routes.jsonc` unchanged
- [x] 3.6 Dogfood: run `clanker-dual-review` at the plan gate on this change from a fresh chat; verify both reviewers run in parallel, overengineering findings are escalated rather than accepted, and the run log and CSV rows are written

## 4. Orchestration Nation rewrite (Claude host)

- [x] 4.1 Write the Implementor role instructions with the high-risk section (security, migrations and data integrity, deploy/rollback) and the handoff contract, plus the `clanker-implementor` agent definition; verify the sections exist
- [x] 4.2 Write the Functional Review role instructions (exercise flows, evidence under `.clanker/functional/<run>/`, skip with reason) and the `clanker-functional-review` agent definition without edit tools; verify the frontmatter tool list
- [x] 4.3 Rewrite `subagents/clanker-orchestration-nation.md`:
  - the finalized-change check, the small-job check, and the small-fix rule
  - the single Implementor thread
  - the code gate through `clanker-dual-review`, Functional Review, and fix cycles with a fresh two-round code gate (max two cycles)
  - the refactor gate and handover with no commit
  - run-log events
  - Verify each development-orchestration spec requirement maps to a section.
- [x] 4.4 Rewrite `subagents/hosts/claude/host.md` and `host.json` for dispatch with `model` and `effort` from `routes.jsonc`, and token capture from subagent completion usage; verify by reading them against the design
- [x] 4.5 Update the installers to install the rewritten coordinator, role references, and the implementor and functional agent definitions; verify by installing to temporary agent roots

## 5. Remove retired pieces

- [x] 5.1 Delete the old pieces and verify `git status` shows only intended deletions:
  - the nine specialist profiles, `subagents/clanker-cross-review.md`, and `subagents/claude/clanker-orchestration-worker.md`
  - `subagents/routing/`, `subagents/scripts/routing_policy.py`, and the old launcher files `cross_review_core.py`, `codex_cross_review.py`, and `claude_cross_review.py` (keep `cross_review.py`, `cross_review_codex.py`, and `clanker_log.py`)
- [x] 5.2 Delete `routing-editor/`, the root `package.json` and `package-lock.json`, the `.gitignore` routing-editor entries, and `skills/legacy/`; verify no file outside `openspec/` references them except the installers' retired-names list (`grep -rn routing-editor --exclude-dir=openspec --exclude-dir=.git .`)
- [x] 5.3 Delete the old tests (`test_routing_policy`, `test_routing_codex_compat`, `test_orchestration_guidance`, `test_review_reservations`, and the old launcher tests `test_claude_cross_review`, `test_codex_cross_review`, and `test_cross_review_{context_access,core,diagnostics,effort,evidence,guidance_paths,process,readiness}`, and `test_cross_review_installers`, which tests the old install set (installers are verified by temporary installs in 3.5, 4.5, and 5.5); keep `test_cross_review` and `test_clanker_log`) and the fixtures `routing_codex_policy6_expected.json`, `codex_doctor.json`, and `codex_models.json`; verify `python3 -m unittest discover tests` passes on the remaining tests
- [x] 5.4 Delete the tracked `.clanker/` logs and reviews; verify `git ls-files .clanker` is empty
- [x] 5.5 Replace the installers' old retirement and backup logic with a hard-coded list of retired installed names that it deletes without backups and prints; verify by installing over a temporary root seeded with the old files
- [x] 5.6 Rewrite the README "Routing Editor" and "Orchestration Nation Hosts" sections for the two-chat workflow and `routes.jsonc`, and update the specialist wording in `global_rules.md` "Delegation and Coordination"; verify no retired role names remain outside `openspec/` and the installers' retired-names list (`grep -rniE "clanker-(architect|backend-developer|data-engineer|devops-engineer|performance-engineer|qa-engineer|test-engineer|ui-developer|ui-ux-reviewer)|routing editor" --exclude-dir=openspec --exclude-dir=.git .`)

## 6. Codex host

- [x] 6.1 Add the Claude Code CLI adapter to the launcher, passing `--add-dir` for the installed skills directory so the reviewer can read the role file and criteria; verify with unit tests using a stubbed CLI, then one real review
- [x] 6.2 Confirm the current Codex collaboration-tool parameters for per-subagent model and effort and for thread continuation (the design's open question); record the answer in `subagents/hosts/codex/host.md`
- [x] 6.3 Rewrite `subagents/hosts/codex/host.md` and `host.json` for the three roles, and add the Codex `routes.jsonc` template; verify by reading them against the design
- [x] 6.4 Update the installers' Codex path to install both skills, the role references, and the Codex `routes.jsonc`; verify by installing to a temporary Codex root
- [x] 6.5 Add the three Codex custom agents (`clanker-implementor`, `clanker-reviewer`, `clanker-functional-review`) mirroring the Claude agent definitions, install them to `<codex-root>/agents/`, and spawn by that name in the Codex host reference; verify by installing to a temporary Codex root and spawning one installed agent in a real Codex session

## 7. Integration

- [ ] 7.1 Run a full Claude-hosted orchestration on a small sample change (implement, code gate, Functional Review or skip, refactor gate, handover); verify the run log, `runs.csv` with per-role models and tokens, and `findings.csv` rows
- [ ] 7.2 Run one Codex-hosted orchestration on the same kind of sample change; verify cross-review uses the Claude adapter and any routing limitations are reported
