# Routing preferences and dispatch preparation

Read **Dispatch procedure** for ordinary orchestration. The remaining sections are
reference material for configuring routes or using the editor.

## Dispatch procedure

### Prepare the run snapshot

Locate `scripts/routing_policy.py` and `routing/` relative to the loaded coordinator
package (source checkout: `subagents/`). Verify Python 3.10+ and read the helper's
`--help`. Disclose the Python prerequisite and global preference source at run
start. Missing Python or invalid configuration blocks routing; there is no silent fallback.

Use the actual target repository and a unique filename-safe run ID. The helper reads
only the explicit global preference path; a missing file means inherit.
Create the snapshot once, under the target repository's `.clanker/routing-snapshots/`:

```text
python <package>/scripts/routing_policy.py snapshot --global <home>/.clanker/orchestration-routing.json --output <repo>/.clanker/routing-snapshots/<run-id>-1.json
python <package>/scripts/routing_policy.py resolve --snapshot <saved-snapshot.json> --request <assignment-request.json>
```

Substitute verified paths. The helper creates an exclusive snapshot containing the
preferences, bundled policy, sources, versions, and fingerprints. Keep it for the run.
Reload only on explicit user direction, with a new ordinal and a logged snapshot link;
do not overwrite previous snapshots or change running workers. Only explicit user
instruction permits `snapshot --bypass <exact-file-path>` for an invalid source.

### Supply the assignment judgment

Use `planning`, `implementation`, `native-review`, `visual-review`, or `claude-review`
for `interaction`, and the full specialist ID for native `role`. Several Claude
specialist profiles still use one `claude-review` route without a native role override.
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

Example request shape (replace the example model/efforts with active runtime evidence):

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

Capability evidence must come from the active collaboration tool, not the saved model
catalog. Supply the advertised supported combinations needed to validate the selected
route. Keep request text free of secrets and private payloads.

### Interpret the result and dispatch

The resolver handles precedence, defaults, fixed/Adaptive effort, profiles, ceilings,
and capability validation. Its JSON includes the selected `model`/`effort`, limitations,
provenance, versions, and snapshot fingerprint. Do not recompute those decisions.

- Native: dispatch only when `dispatch_allowed` is true, using the exact returned pair.
- Claude: `requires_launcher_preflight` with `launcher_allowed` permits only the guarded
  `claude_cross_review.py` launcher with explicit resolved `--model` and `--effort`.
  Follow the cross-review reference; do not invent capability evidence or bypass preflight.
- Errors or blocked results: report the concrete limitation and continue independent
  work. Do not substitute models, raise effort, or bypass invalid configuration silently.

Disclose consequential limitations, including ceiling
constraints or low fixed effort. Profiles express policy, not quality guarantees.
A successful resolver exit or preview is not proof of dispatch or model execution.

### Capture routing evidence without rewriting it

The snapshot command saves its output when `--output` is supplied. The resolve command
only prints JSON; capture that output and append it as a compact JSON code block in the
assignment's run-log event before dispatch. Do not manually transcribe its fields.

Record the snapshot path and configuration source paths once per snapshot. Alongside
each decision, record explicit `session_override` values (absent from the decision
JSON), assignment ID/ownership, and instruction path. The generated decision preserves
schema/policy versions, fingerprint, tier/reason, mode, proposed/requested effort,
ceiling effects, provenance, and capability status. Summarize only meaningful limitations.

Record dispatch success/failure separately, with observed model/effort only when the
runtime reports them; otherwise use unknown. Preserve earlier attempts and snapshot
records. The parent owns these writes; neither resolver previews nor worker reports
establish successful execution.

## Preferences and inheritance

Sparse documents contain `schema_version: 1`, optional `agents`, `interactions`, and
`adaptive_profiles`. Native `agents` entries contain a model and/or reasoning and
use the existing native role IDs. Claude continues to use `interactions.claude-review`.
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
      "reasoning": {"mode": "adaptive", "max_effort": "max"}
    }
  }
}
```

This sets a shared backend-agent default, retaining any activity exceptions. Editing
an agent field never deletes its activity exceptions; removing that field restores
inheritance. Requests without a native role ignore agent defaults.

This permits, but does not force, max for Luna. A straightforward assignment uses high under
the provisional bundled mapping. Demanding work maps to max only when its cap
permits it. All mappings are editable policy, not measured quality guarantees.
A new exact model ID works with fixed effort when runtime evidence supports it;
Adaptive needs a complete profile keyed `codex:<model>` or `claude:<model>` with
`tiers` for straightforward/involved/demanding and `default_ceiling`.

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
startup-only choice is visible in provenance and cannot be changed by the browser.

The editor saves only its fixed global destination,
validates first, and preserves drafts on failed/conflicting saves. Reset saves an
empty versioned override document. Invalid saved JSON is never silently replaced;
explicitly repair/reset it in the editor. Linked paths below the pinned roots are
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
Only policy-version-4 snapshots are supported. Older or unknown snapshot versions
are rejected with instructions to start a new run. Reinstalling the bundle preserves
global preferences. Preference/API schema remains 1.

Complete legacy profiles normalize in memory: routine becomes straightforward,
complex becomes involved, exceptional becomes demanding, and default_ceiling stays
unchanged. Mechanical is retired; its old assignments can receive a different effort.
Opening, previewing, and reinstalling never rewrite preferences. The editor marks
pending conversion and allows Save without further edits. Save backs up exact original
bytes next to the global file as `orchestration-routing.json.pre-three-tier.<sha256>.bak`
before writing current profiles. A backup failure or revision conflict prevents the
write; project files are untouched. To roll back, stop the editor and restore that
backup to `orchestration-routing.json`, together with compatible helpers/assets.
Backups contain the entire original document, including retired mechanical values.
