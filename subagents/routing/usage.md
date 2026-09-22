# Routing preferences and dispatch preparation

Use the `routing_policy.py` and `routing_editor.py` files in the loaded coordinator's
`scripts/` directory. Their policy data and this guide live in `routing/`. In the
source checkout the package root is `subagents/`; in an installed skill it is the
directory containing `SKILL.md`. Verify the actual Python 3.10+ executable and read
`--help`. Node is needed only to develop/build the optional React editor.

## Snapshot once, resolve each assignment

The parent resolves the actual target repository and creates a unique run ID. Read
`~/.clanker/orchestration-routing.json` and the target project's optional
`.clanker/orchestration-routing.json`. Missing files mean inherit; invalid present
files block. Do not search parent repositories or infer another project's settings.
The CLI takes explicit paths, allowing isolated tests without changing real global
preferences. A missing Python executable blocks all configured routing, including a
run using bundled defaults.

Create an exclusive parent-owned snapshot file beneath the target project's
`.clanker/routing-snapshots/`, with an unused filename-safe run ID and ordinal.
For example, replace timestamp colons with hyphens for Windows filenames; retain
the original run ID in the log. The helper creates missing parent directories. Example command
shape (substitute verified absolute paths; do not copy placeholders literally):

```text
python <package>/scripts/routing_policy.py snapshot --global <home>/.clanker/orchestration-routing.json --project <repo>/.clanker/orchestration-routing.json --output <repo>/.clanker/routing-snapshots/<run-id>-1.json
python <package>/scripts/routing_policy.py resolve --snapshot <saved-snapshot.json> --request <assignment-request.json>
```

The snapshot freezes exact input documents and bundled policy plus fingerprints;
resolve validates it and does not reread live preferences. Keep it for the run.
For an explicitly requested reload create the next ordinal; never overwrite the old
snapshot. Log the new fingerprint before subsequent assignments. Snapshot hashes
identify content, not an authenticated claim about model availability.

Only an explicit user instruction authorizes `snapshot --bypass <exact-file-path>`.
It ignores that entire named file for this run and records the bypass. Do not use it
to work around an error on your own initiative.

## Inputs and interpretation

An assignment request has an interaction, optional native specialist ID, assessed
tier, concise reason, risk flags, optional explicit worker overrides, and available
runtime capabilities. Example for a bounded native assignment:

```json
{
  "interaction": "implementation",
  "role": "clanker-backend-developer",
  "tier": "routine",
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

The capability values above are illustrative: transcribe the active runtime's
actual advertised combinations, not this example or the bundled model catalog.
Native dispatch requires a supported exact requested pair. Unknown/unsupported
combinations block without fallback. Evidence is parent-attested and does not
prove the worker's observed effective settings. Keep observed values unknown unless
the runtime reports them. Supply worker `model` and `reasoning_effort` from the
resolved decision, using an empty or bounded-history fork; never a full-history fork
when requesting different settings.

`session_override` means the user's explicit request for this worker assignment;
it never means the model/effort selected for the parent session. Available interactions:
`planning`, `implementation`, `native-review`, `visual-review`, `claude-review`.
Use full specialist IDs from the role catalog only for native routes. Multiple
Claude specialist instructions still share one `claude-review` route.

Tier assessment is a parent judgment, not automatic semantic classification by
Python. Mechanical is a clear transformation, routine is bounded work, complex
covers uncertainty or consequential risk, and exceptional requires a specific
reason for unusually difficult reasoning. `security`, `data-integrity`, or `recovery`
risk imposes at least complex. Other flags: `cross-layer`, `uncertainty`, `performance`.
Fixed effort remains authoritative. Adaptive maps the tier through the selected
model's profile and ceiling; model choice alone does not justify max. An explicit
inherited cap persists through a model-only override. Omitting/resetting the cap
uses the model profile default. Disclose limiting caps and low fixed effort for
consequential work; do not claim quality equivalence or silently change models.

For Claude, resolve without inventing capability evidence. A
`requires_launcher_preflight` result with `launcher_allowed` permits only calling
the existing `claude_cross_review.py` with explicit resolved `--model` and `--effort`.
It does not authorize direct model execution or bypass preflight. The launcher checks
subscription authentication and CLI controls before requesting the review. Reconcile
its report, record any blocked/failed execution, and retain the ordinary review
checkpoint and recheck rules. A direct launcher call without `--model` still defaults
to Opus 5 and still requires explicit `--effort`.

## Preferences and inheritance

Sparse documents contain `schema_version: 1`, optional `agents`, `interactions`, and
`adaptive_profiles`. Native `agents` entries contain a model and/or reasoning and
use the existing native role IDs. Claude continues to use `interactions.claude-review`.
Merge order for each route field is bundled defaults, global interaction, global
agent default, global activity-specific specialist, project interaction, project
agent default, project activity-specific specialist, then explicit worker override. Reasoning objects and individual profile maps are atomic units.
Disclose active project overrides at run start. User-selected project precedence is
intentional; the editor does not add a separate trust/consent system.

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

This permits, but does not force, max for Luna. A routine assignment uses high under
the provisional bundled mapping. Exceptional work maps to max only when its cap
permits it. All mappings are editable policy, not measured quality guarantees.
A new exact model ID works with fixed effort when runtime evidence supports it;
Adaptive needs a complete profile keyed `codex:<model>` or `claude:<model>` with
`tiers` for mechanical/routine/complex/exceptional and `default_ceiling`.

## Run evidence

Log the snapshot path/fingerprint, schema/policy version, field sources, interaction,
role, assessed tier/factors, fixed/Adaptive mode, proposed versus requested effort,
ceiling/source, capability state, overrides, and requested versus observed settings.
For example, a ceiling-limited Luna exceptional assignment records proposed max,
requested xhigh, its cap source, and unknown observed effort until reported. A failed
dispatch stays failed; a preview never counts as execution. Keep these concise and
parent-owned; never log credentials or hidden reasoning.

## Editor and persistence

Build in `routing-editor/` using `npm ci` then `npm run build`. From the checkout:

```text
python subagents/scripts/routing_editor.py --project <target-project>
```

From an installed package use its `scripts/routing_editor.py`. Wrangler copies the
build only when present; no Node runtime is needed for the built editor. Open the
printed loopback URL. Its per-process session token is consumed from the fragment
and removed from browser history. Stopping the process invalidates the session.
For isolated checks pass `--global-config-dir <temporary-global-directory>`; this
startup-only choice is visible in provenance and cannot be changed by the browser.

The editor saves only its selected global or startup-selected project destination,
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

These preserve the option to version `.clanker/orchestration-routing.json`. Reinstall
updates package defaults/helpers, never preference files. A build/helper version
mismatch is an error; rebuild/reinstall. Removing overrides restores defaults.
New snapshots use policy version 2; previously frozen policy-1 snapshots retain their
original resolution and reported version. Preference/API schema remains 1. An older
helper rejects the new `agents` key rather than silently ignoring it. For rollback,
restore a deliberately exported pre-agent preference document with compatible
helpers/assets; the editor does not create an automatic backup.
