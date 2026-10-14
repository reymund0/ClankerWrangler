# Routing preferences and dispatch preparation

Read **Dispatch procedure** for ordinary orchestration. The remaining sections are
reference material for configuring routes or using the editor.

## Dispatch procedure

### Prepare the run snapshot

Locate `scripts/routing_policy.py` and `routing/` relative to the loaded coordinator
package (source checkout: `subagents/`). Verify Python 3.10+ and read the helper's
`--help`. Disclose the Python prerequisite, the orchestration host, and the global
preference source at run start. Missing Python or invalid configuration blocks routing;
there is no silent fallback.

The host comes from the installed `routing/host.json`, which also names the host's
preference file under `<home>/.clanker/`:

| Host | `host` | `preferences_file` | External review interaction |
| --- | --- | --- | --- |
| Codex-led | `codex` | `orchestration-routing.json` | `claude-review` |
| Claude-led | `claude` | `orchestration-routing-claude.json` | `codex-review` |

Use the actual target repository and a unique filename-safe run ID. The helper reads
only the explicit global preference path; a missing file means inherit. The two hosts
use separate files with the same schema, and neither host reads or changes the other's
file. Create the snapshot once, under the target repository's `.clanker/routing-snapshots/`:

```text
python <package>/scripts/routing_policy.py snapshot --global <home>/.clanker/<preferences_file> --output <repo>/.clanker/routing-snapshots/<run-id>-1.json
python <package>/scripts/routing_policy.py resolve --snapshot <saved-snapshot.json> --request <assignment-request.json>
```

Substitute verified paths and the `preferences_file` read from `routing/host.json`.
Without `--host`, the snapshot takes the installed host. When `routing/host.json` is
absent (a source checkout), the helper defaults to `codex`; for any other host the user
must name it and the parent passes `--host claude` explicitly. Never infer the host.
An explicit `--host` that contradicts an installed `routing/host.json`, or a `--global`
file name that is not the installed host's preference file, is rejected before any
preference file is read. An invalid or unknown `routing/host.json` blocks routing.

The helper creates an exclusive snapshot containing the host, preferences, bundled
policy, sources, versions, and fingerprints. Keep it for the run.
Reload only on explicit user direction, with a new ordinal and a logged snapshot link;
do not overwrite previous snapshots or change running workers. Only explicit user
instruction permits `snapshot --bypass <exact-file-path>` for an invalid source.

### Supply the assignment judgment

Use `planning`, `implementation`, `native-review`, `visual-review`, or the host's
external review (`claude-review` under the Codex host, `codex-review` under the Claude
host) for `interaction`, and the full specialist ID for native `role`. Several specialist
profiles in one external review still use one route without a native role override.
The other host's external review ID is rejected.
`session_override` contains only explicit user choices for this assignment, never
inferred parent-session settings.

Assess `tier` from the reasoning this assignment needs, independently of model:

- `straightforward`: established approach, limited decisions, and direct checks;
  for example, extend a handler using an existing validated pattern.
- `involved`: meaningful decisions, bounded uncertainty, or interacting behavior;
  for example, coordinate a handler and UI with understood compatibility constraints.
- `demanding`: substantial unresolved reasoning across coupled constraints or
  difficult correctness conditions; for example, establish a safe recovery protocol
  when concurrent state transitions and failure ordering are still unresolved.

Supply one tier and one short assignment-specific `reason`; no scorecard or extra
assessment fields are required. Reassess each new assignment: investigation may be
demanding while implementation of its established solution is straightforward.
Include applicable `risk_flags`: `security`, `data-integrity`, `recovery`,
`cross-layer`, `uncertainty`, or `performance`. The first three impose at least
involved, but only when that worker owns the consequential behavior. A copy change
on a security page does not itself make the worker responsible for authorization.
File count, role, project importance, or model price alone do not select the tier.

Example request shape under the Codex host (replace the example model/efforts with
active runtime evidence):

```json
{
  "interaction": "implementation",
  "role": "clanker-backend-developer",
  "tier": "straightforward",
  "risk_flags": [],
  "reason": "Bounded handler change with a defined input contract",
  "session_override": {},
  "capabilities": {
    "provider": "codex",
    "source": "Active collaboration tool description, transcribed by the parent",
    "models": {"gpt-5.6-terra": ["low", "medium", "high", "xhigh", "max", "ultra"]}
  }
}
```

Under the Claude host, native `capabilities.provider` is `claude`. Its `models` lists
exactly the model values the active Agent tool advertises for per-call use (aliases such
as `sonnet`, `opus`, `haiku`, `fable`) with the efforts it accepts, and `overrides`
lists route-replacing runtime settings the parent observed:

```json
{
  "interaction": "implementation",
  "role": "clanker-backend-developer",
  "tier": "straightforward",
  "risk_flags": [],
  "reason": "Bounded handler change with a defined input contract",
  "session_override": {},
  "capabilities": {
    "provider": "claude",
    "source": "Active Agent tool model and effort options, transcribed by the parent",
    "models": {"haiku": ["low", "medium", "high", "xhigh", "max"]}
  },
  "overrides": []
}
```

Capability evidence must come from the host's active subagent mechanism, not the saved
model catalog. Supply the advertised supported combinations needed to validate the
selected route. An exact model ID such as `claude-sonnet-5-5` is dispatchable only when
the runtime advertises that exact string with the requested effort; it is never
translated to an alias. External review routes (`claude-review`, `codex-review`) need
no native catalog: omit `capabilities` or supply `{"provider": "<reviewer provider>",
"source": "...", "preflight_valid": true}` after the launcher's preflight passes.

`overrides` is an optional list of unique setting names (for example
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, `CLAUDE_CODE_EFFORT_LEVEL`, or `agent.spawn hook`)
that the parent observed and that would replace the requested model or effort. Any entry
makes the decision `blocked_by_override` with `dispatch_allowed` false and a limitation
naming the setting; the helper never predicts the substituted value, and the decision
still shows the requested model and effort. Overrides apply to native dispatch requests
only: a non-empty `overrides` on an external review request (`claude-review`,
`codex-review`) is rejected at `request.overrides`, because the launcher preflight checks
the reviewer's own overrides. A plain `CLAUDE_CODE_SUBAGENT_MODEL` without `_FORCE` does not replace an
explicit per-call model, so it is not an override. Keep request text free of secrets and
private payloads.

### Interpret the result and dispatch

The resolver handles precedence, defaults, fixed/Adaptive effort, profiles,
and capability validation. Its JSON includes the selected `model`/`effort`, limitations,
provenance, versions, and snapshot fingerprint. Do not recompute those decisions.

- Native: dispatch only when `dispatch_allowed` is true, using the exact returned pair.
- External review: `requires_launcher_preflight` with `launcher_allowed` permits only the
  guarded launcher named in `routing/host.json` (`claude_cross_review.py` or
  `codex_cross_review.py`) with explicit resolved `--model` and `--effort`.
  Follow the cross-review reference; do not invent capability evidence or bypass preflight.
- Errors or blocked results: report the concrete limitation and continue independent
  work. Do not substitute models, raise effort, or bypass invalid configuration silently.

Disclose consequential limitations, including unsupported requests or low fixed
effort. Profiles express policy, not quality guarantees.
A successful resolver exit or preview is not proof of dispatch or model execution.

### Capture routing evidence without rewriting it

The snapshot command saves its output when `--output` is supplied. The resolve command
only prints JSON; capture that output and append it as a compact JSON code block in the
assignment's run-log event before dispatch. Do not manually transcribe its fields.

Record the snapshot path, host, and configuration source paths once per snapshot. Alongside
each decision, record explicit `session_override` values (absent from the decision
JSON), assignment ID/ownership, and instruction path. The generated decision preserves
host, provider, execution kind (`native` or `external`), schema/policy versions,
fingerprint, tier/reason, mode, proposed/requested effort, provenance and capability
status, and reports any `overrides` it was given. Summarize only meaningful limitations.

Record dispatch success/failure separately, with observed model/effort only when the
runtime reports them; otherwise use unknown. Preserve earlier attempts and snapshot
records. The parent owns these writes; neither resolver previews nor worker reports
establish successful execution.

## Preferences and inheritance

Sparse documents contain `schema_version: 1`, optional `agents`, `interactions`, and
`adaptive_profiles`. Native `agents` entries contain a model and/or reasoning and
use the existing native role IDs. The host's external review uses its own interaction
key: `interactions.claude-review` in the Codex file and `interactions.codex-review` in
the Claude file; the other host's key is rejected at its field path. Native routes use
the host's provider and the external review uses the other provider, so a model known to
belong to the wrong provider is rejected. Adaptive profiles stay keyed
`<provider>:<model>` in each file. Bundled Adaptive profiles are host-scoped: the Codex
host keeps its existing profiles, while the Claude host bundles `claude:sonnet`,
`claude:haiku`, `claude:opus` (medium/high/high) and `codex:gpt-6.1-sol`
(medium/high/xhigh). Claude-host defaults are Sonnet for planning, native review and
visual review, Haiku for implementation, and `gpt-6.1-sol` for `codex-review`, all Adaptive.
Merge order for each route field is bundled defaults, global interaction, global
agent default, global activity-specific specialist, then explicit worker override.
Reasoning objects and individual profile maps are atomic units.
Project preference files are ignored and left untouched; they are not imported into
the global configuration.

```json
{
  "schema_version": 1,
  "agents": {
    "clanker-backend-developer": {
      "model": "gpt-5.6-luna",
      "reasoning": {"mode": "adaptive"}
    }
  }
}
```

This sets a shared backend-agent default, retaining any activity exceptions. Editing
an agent field never deletes its activity exceptions; removing that field restores
inheritance. Requests without a native role ignore agent defaults.

Adaptive requests the assessed tier's mapping directly. A straightforward Luna
assignment uses high under the provisional bundled mapping; demanding work requests
max. Each tier retains its configured value. All mappings are editable policy, not
measured quality guarantees, and runtime capability checks still apply.
A new exact model ID works with fixed effort when runtime evidence supports it;
Adaptive needs a complete profile keyed `codex:<model>` or `claude:<model>` with
only `tiers` for straightforward/involved/demanding. Adaptive reasoning contains
only `mode: adaptive`. Retired `max_effort` and `default_ceiling` fields fail existing
strict validation; they are not ignored, stripped, or migrated. Decisions and effective
routes omit `ceiling` and `ceiling_source`; `proposed_effort` equals requested effort.

## Editor and persistence

Build in `routing-editor/` using `npm ci` then `npm run build`. From the checkout:

```text
python routing-editor/scripts/routing_editor.py
```

From an installed package use its `scripts/routing_editor.py`. Wrangler copies the
build only when present; no Node runtime is needed for the built editor. Open the
printed loopback URL. Its per-process session token is consumed from the fragment
and removed from browser history. Stopping the process invalidates the session.
For isolated checks pass `--global-config-dir <temporary-global-directory>`; this
startup-only choice is visible in provenance, applies to both hosts' files, and cannot
be changed by the browser.

The editor has a host selector. Each host has its own fixed destination
(`orchestration-routing.json` for Codex, `orchestration-routing-claude.json` for Claude),
revision, save lock and draft; saving one host never changes the other's file. Preview
resolves through the same resolver and host snapshot used for dispatch. The editor saves
only those fixed global destinations,
validates first, and preserves drafts on failed/conflicting saves. Reset prepares an
empty versioned override draft; a separate explicit Save replaces all overrides.
Invalid saved JSON reports its field-path error and is never silently replaced.
Hand-edit retired keys to preserve customizations, or explicitly save a valid
replacement document. Linked paths below the pinned roots are
rejected. Saves use an owner-attributed exclusive lock, final revision check and
atomic replacement. Two editor instances cannot silently overwrite each other;
an unrelated editor can still race after the final check. A leftover `.lock` reports
its owner record: verify that process has exited before manually removing that lock.

Recommended target-project ignore patterns (documentation only; neither installer
nor editor changes the target project's ignore file):

```gitignore
.clanker/*.md
.clanker/reviews/
.clanker/routing-snapshots/
.clanker/*.lock
.clanker/*.tmp
```

Project routing preferences are no longer supported. Reinstall
updates package defaults/helpers, never preference files. A build/helper version
mismatch is an error; rebuild/reinstall. Removing overrides restores defaults.
Only policy-version-7 snapshots are supported. Older or unknown snapshot versions
are rejected with instructions to start a new run. Reinstalling the bundle preserves
global preferences. Preference/API schema remains 1.

## Policy 6 to 7 upgrade

Policy 7 adds the orchestration host. Snapshots, effective configuration and decisions
record `host`, and decisions and effective interactions add `provider` and `execution`.
Policy-6 snapshots are rejected with instructions to start a new run; they are not
replayed or rewritten. Install the complete bundle, which includes the matching
`routing/policy.json`, helpers and editor assets (`compatibility.json` now names policy
7), then start new runs. Codex-led behavior is unchanged: the existing
`~/.clanker/orchestration-routing.json` keeps its path, bytes, precedence and defaults,
and no Claude file is created; a missing Claude file means bundled defaults. Rollback
restores the previous bundle and matching assets. Preference files need no rollback and
the Claude-host file is ignored by policy-6 helpers.

For the policy-4 to policy-5/6 cutover, pause routing and retain an owner-managed original preference
file if rollback is needed. Deploy the complete bundle and compatible editor assets,
then hand-remove `default_ceiling` from every custom profile and `max_effort` from
every route before starting a new run. Policy 4 requires profile ceilings and policies 5 and 6
reject them; custom-profile documents cannot satisfy both versions. Optional route
`max_effort` alone can be removed early. Installers never edit global preferences or
create ceiling-migration backups. Rollback restores the old bundle, matching assets,
and the original matching preference file, then starts a new run.

Complete legacy profiles without retired ceiling fields normalize in memory: routine
becomes straightforward, complex becomes involved, and exceptional becomes demanding.
Mechanical is retired; its old assignments can receive a different effort.
Opening, previewing, and reinstalling never rewrite preferences. The editor marks
pending conversion and allows Save without further edits. Save backs up exact original
bytes next to the global file as `orchestration-routing.json.pre-three-tier.<sha256>.bak`
before writing current profiles. A backup failure or revision conflict prevents the
write; project files are untouched. To roll back, stop the editor and restore that
backup to `orchestration-routing.json`, together with compatible helpers/assets.
Backups contain the entire original document, including retired mechanical values.

## Retired specialist profiles (policies 6 and 7)

Policies 6 and 7 have ten native roles. `clanker-ux-designer`, `clanker-documentation-writer`,
and `clanker-product-engineer` are retired and are rejected in requests and preferences.
The parent owns product scope, acceptance criteria, and routine documentation. Supplied
Claude Design handoffs guide UX implementation; the UI/UX reviewer still verifies
rendered states and interactions.

To preserve other customizations, hand-edit the global preference file outside the
editor and remove all three IDs from `agents` and from each
`interactions.<activity>.specialists` map. Validation reports the first invalid field;
check both locations in one pass. Reload after editing, and use the latest revision
before saving. Invalid saved preferences expose no usable document in the editor.
Reset prepares a whole-document replacement draft; a separate Save replaces all
overrides. It is not selective cleanup. Existing ceiling-field rejection still applies.

Upgrade the complete helpers, policy data, and matching editor assets at a safe point,
then start a new run: policy-5 snapshots are not replayed or rewritten. Update the
tracked `routing-editor/public/compatibility.json` when developing the package;
Vite copies it to `dist` rather than generating a new policy version.

Both installers check retirement sources and ancestors, entry types, and backup
parents before replacement-bundle writes. An explicitly chosen agent root may itself
be a link; checks still reject linked components below that root. Retired references
must be regular files; retired standalone skills must be ordinary directories.
Descendant links/junctions, escaping
paths, and unexpected types are refused. Retained-role standalone migration keeps
its existing behavior. Unrelated references, custom notes, and preferences are preserved.

After the new bundle is ready, retired entries move into
`<agent-root>/backups/orchestration-nation/`. Reference backups use `<id>.md`, then
`<id>-2.md`, `<id>-3.md`; standalone directory backups use `<id>`, then `<id>-2`,
`<id>-3`. Existing backups are preserved. Repeating a successful install creates no
additional retirement backups. The installer reports each source and destination.

A preflight or move failure aborts with a nonzero exit. Later entries, steps, and
agent roots are not processed. Completed writes and backups remain: a failed move
can leave new helpers with unfinished retirement/rules copying, and later-root
failure can leave mixed package versions. Fix the reported cause and rerun to finish
remaining work without duplicating completed backups. There is no automatic rollback.
For rollback, restore the previous complete bundle and matching assets; restore any
owner-changed preferences and custom instructions from their retained backups, then
start a run matching the restored helper version. Preserve backup history.

Use explicit temporary agent destinations for installer tests. `--global-config-dir`
isolates preferences only; do not activate Run Wrangler during rendered acceptance
against real agent roots.
