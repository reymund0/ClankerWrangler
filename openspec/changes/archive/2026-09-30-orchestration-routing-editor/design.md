## Context

See proposal.md for motivation and the five delta specifications for acceptance criteria. The repository currently distributes Markdown instructions with PowerShell/Bash installers and a Python standard-library Claude launcher. There is no React app or configuration resolver. Codex native collaboration exposes model/effort arguments to the parent; a Python helper cannot dispatch native workers itself. Claude's launcher already takes explicit model/effort and enforces subscription and read-only review restrictions.

The user selected global defaults with optional project overrides. This change creates an optional editor and a shared resolver, keeping the existing one-visible-skill package and parent-selected session settings.

## Goals / Non-Goals

**Goals:** Provide repeatable route resolution, understandable inheritance, model-aware Adaptive effort, and local persistence. Keep runtime orchestration independent of a running web server or Node installation. Separate human/model task assessment from deterministic configuration evaluation.

**Non-Goals:** Automatic model switching, cost prediction, learned routing from telemetry, arbitrary workflow graphs, task execution from the editor, hosted services, and Claude-led orchestration. A ceiling limits reasoning effort, not dollars, tokens, or wall time. No provider credentials belong in these files. Do not replace the existing Claude launcher or create another agent framework.

## Decisions

### 1. Five interactions, with optional native role overrides

Use stable interaction IDs: `planning`, `implementation`, `native-review`, `visual-review`, and `claude-review`. Planning includes product/architecture/UX/QA strategy; implementation includes bounded tests and documentation authoring; native review covers code/security and domain critiques; visual review requires rendered evidence. Assign the interaction from the actual work, not a specialist's job title. Keep rechecks in the original interaction while reassessing remaining risk.

Native specialist overrides live within their interaction. Claude receives one interaction route even when its packet includes multiple specialties, avoiding a highest-effort/first-role tie-breaker that the user never chose. The editor shows parent settings as session-controlled with unknown actual settings when unavailable.

Alternative: per-role settings alone would couple planning and implementation unnecessarily; dozens of predefined scenarios would make the initial UI difficult to use.

### 2. Layered JSON outside the installed package

Use `~/.clanker/orchestration-routing.json` for global preferences and `<target-project>/.clanker/orchestration-routing.json` for project overrides. Resolve the user's home using platform facilities, independently of Codex installation roots. An optional startup-only `--global-config-dir` selects an alternative global preferences directory for isolated testing or deliberate user configuration; the default remains ~/.clanker. Its resolved path is recorded in provenance and cannot be changed by an HTTP request. The resolver snapshot CLI accepts an explicit global file path. The editor receives the project explicitly at startup; the coordinator supplies its verified target repository. A missing project selection disables project editing. These paths are proposed new conventions, not existing configuration.

Bundle schema/default/catalog data under `subagents/routing/`, installed as `routing/` within the coordinator package. Add Python helpers under `subagents/scripts/`. User files contain `schema_version: 1` and sparse `interactions` and `adaptive_profiles` objects. Defaults include `policy_version`; the resolver snapshots exact inputs and their hashes per run.

Each interaction may contain `model`, an atomic `reasoning` value (`{mode: fixed, effort: ...}`, `{mode: adaptive}`, or `{mode: adaptive, max_effort: ...}`), and native `specialists` keyed by the existing catalog role IDs. Cross-review has no specialist route overrides. Adaptive profiles are keyed by provider plus exact model ID and contain a complete four-tier effort map and default ceiling. All five bundled routes use `{mode: adaptive}`. An omitted Adaptive max_effort resolves to the effective model profile default ceiling. Any explicit max_effort inherited from a user layer remains authoritative even when a higher layer changes only the model; incompatible values block rather than disappear. Resetting reasoning to `{mode: adaptive}` deliberately restores the model default ceiling. For fixed reasoning, changing only a model retains the chosen effort and reports incompatibility if necessary.

Resolution is field-wise: bundled values, global interaction, global specialist, project interaction, project specialist, session override. This intentionally lets a project interaction choice override a global specialist choice. Replace reasoning objects atomically. Adaptive profile maps resolve bundled -> global -> project as complete maps; session requests can override model/reasoning but do not mutate saved maps. Omitted means inherit; reject null, unknown keys, invalid role/interaction combinations, and unsupported schema versions with field-specific errors. An invalid present layer blocks routing rather than masquerading as an absent file. Only an explicit user instruction permits a run-only bypass; it names the ignored file and is logged. Disclose project override sources and effective changes at run start. Project preferences are intentionally authoritative within the explicit precedence the user selected; no new trust-confirmation system is introduced. For consequential work, a fixed effort below the mapped Adaptive recommendation must be disclosed as a limitation without overriding the explicit fixed choice. Apply the same pinned-root link/reparse checks to configuration reads as to writes.

Alternative: putting preferences inside the installed bundle would lose them on reinstall; flattening inherited settings into each project would freeze global defaults unintentionally.

### 3. Adaptive is a transparent mapping, not a quality claim

The parent supplies `interaction`, native `role` when applicable, `tier`, risk flags, concise reason, and transient session overrides. Inputs also include a run snapshot and any available runtime capability evidence. Mechanical means bounded transformations with clear checks; routine means clear interfaces and ordinary implementation/review; complex includes uncertain interfaces or consequential security/data/recovery risks; exceptional means unusually difficult reasoning with a specific explanation. Consequential flags impose at least complex. Do not derive effort solely from file count or the selected model. Invalid tier/risk combinations are normalized upward with that reason disclosed; exceptional requires its own explanation.

Initial model-specific maps are provisional user-editable policy, not benchmark results:

| Model profile | Mechanical | Routine | Complex | Exceptional | Default ceiling |
| --- | --- | --- | --- | --- | --- |
| Astra / Sol / Terra | low | medium | high | xhigh | xhigh |
| Luna | medium | high | xhigh | max | xhigh |
| Claude review (Opus 5 and verified CLI IDs default, opus[1m], claude-fable-5-1[1m], sonnet) | low | medium | high | high | high |

Thus Luna exceptional work reaches max only when the user sets a ceiling permitting it. A lower ceiling is honored and reported as limiting the recommendation; the system can recommend a stronger model or independent review without altering the route. Fixed effort bypasses Adaptive and records the explicit choice. Effort ordering is provider-scoped; do not assume every model supports every enum. Other models can use an explicit supported fixed effort immediately, or Adaptive after the user supplies a complete supported mapping. The implementation must verify available model identifiers and efforts against current runtime/official evidence rather than treat this table as an entitlement claim.

Return a structured decision with requested model/effort, proposed effort, tier, rationale, ceiling/limitations, per-field sources, schema/policy version, snapshot hashes, and capability state. Identical explicit inputs produce identical output. Task classification itself remains a judgment by the parent; do not promise identical classification across model runs.

### 4. One Python resolver, two callers

Implement the resolver with Python 3.10+ standard-library facilities and expose a JSON CLI. The local editor service imports the same module for preview; React displays returned decisions and does not reimplement precedence or effort selection. Shared data defines editor choices and validation. The resolver never executes models or shell commands.

The coordinator reads a snapshot at run start, calls the resolver before each assignment, checks active native tool capabilities, logs the decision, then dispatches using explicit model and reasoning arguments with a bounded-history or empty-history fork. The active collaboration tool description/schema is native capability evidence: this session advertises exact model IDs and their supported reasoning levels. The parent supplies those advertised combinations, with source and runtime identity, rather than treating bundled catalog entries or a prior invocation as current proof. Unknown capability metadata blocks native dispatch until supported runtime evidence is supplied. The standalone UI normally lacks that evidence and labels previews unverified. Requested and observed settings remain distinct; dispatch failure is not proof of unavailable settings being substituted.

For Claude, the coordinator first resolves the requested model/effort without capability evidence, producing `requires_launcher_preflight` and `launcher_allowed: true` (not permission to execute a model without checks). It then passes explicit `--model` and `--effort` to the existing launcher. Only the launcher may advance to model execution after its built-in subscription/capability preflight succeeds; its report supplies the final preflight/execution outcome. No new preflight-only CLI mode or duplicated preference loader is needed. CLI preflight remains authoritative for supported controls/effort, authentication, and execution restrictions; actual account/model availability may only be learned from invocation, which must fail honestly with no fallback. Retain direct CLI Opus 5 default and required explicit effort. Do not add a second preference loader to the Claude launcher. Native tool catalogs and Claude preflight are different sources; a UI model catalog alone proves neither availability nor entitlement.

Use a parent-owned `.clanker/routing-snapshots/<run-id>-<ordinal>.json` containing exact bundle, input documents, sources and hashes, created exclusively by the resolver `snapshot` command. Every dispatch preparation uses `resolve --snapshot <path>` and validates the stored fingerprint without re-reading preferences. Reload explicitly creates a new ordinal snapshot; retain old snapshots for run reproduction. Log the run snapshot once, reference it on assignment decisions, and record explicit reloads as new snapshots. Saving in the UI affects new runs; a user-requested reload can affect future assignments only, never already-running workers or historical outcomes.

Alternative: implementing routing in both TypeScript and Python risks preview/dispatch drift; a Markdown-only policy cannot reliably validate precedence and capabilities.

Provider and gate contract: infer `codex` for native interactions and `claude` for cross-review; profile keys are `<provider>:<exact-model-id>`, and mismatched provider IDs are invalid. Native capability evidence must advertise the exact requested model and effort, otherwise status is `unverified` or `unsupported` with `dispatch_allowed: false`. Claude CLI evidence may produce `preflight_valid` with `dispatch_allowed: true` and `account_status: unverified`; actual invocation reports account/model acceptance or failure. A native preview with no evidence remains `unverified`; a Claude preview without evidence reports `requires_launcher_preflight` and does not itself execute anything. `dispatch_allowed` is false until capability/preflight evidence is present, while `launcher_allowed` permits only the existing guarded Claude launcher. Do not equate a valid catalog entry with validated runtime access. Include `ceiling_source` separately from model and reasoning sources. Explicit session overrides always mean per-assignment worker overrides, never the parent's active session settings.

Persistence/UI details: a bypass ignores the entire explicitly named preference file. Reset persists a valid empty versioned override document instead of deleting it. Canonicalize the selected home/project roots once at startup, then reject linked/reparse components below those pinned roots, including `.clanker` and the destination file. Installed editor files occupy only the package-owned `editor/` directory, with a compatibility manifest; stale-asset cleanup must verify containment and reject reparse traversal. Project preferences remain versionable with selective ignore rules for `.clanker/*.md` and `.clanker/reviews/`, plus `.clanker/routing-snapshots/`, `.clanker/*.lock`, and `.clanker/*.tmp`, not a blanket `.clanker/` ignore. These are documentation-only recommendations for target projects; the editor and installer do not edit their ignore files. Lock files use a .lock suffix and owned temporary files a .tmp suffix.

### 5. Small React app and opt-in local server

Create `routing-editor/` with React, React DOM, TypeScript, and Vite, using ordinary CSS and native form controls initially. Verify compatible versions and commit a lockfile during apply. Use focused component tests and a rendered browser verification pass; choose the smallest compatible test tooling then. No UI component library, desktop wrapper, database, or server framework is needed.

A Python standard-library server serves the built static app and a narrow JSON API for load, validate/preview, and save. It binds explicitly to `127.0.0.1` on a chosen/ephemeral port. Startup accepts a project directory as a command-line argument and resolves it once. The browser sends only global/project scope, never arbitrary filesystem paths. Support source and installed-package asset locations. Document an explicit build and start command; launching the editor is opt-in and cannot invoke agents.

Each launch generates a short-lived unguessable session token; bootstrap it through the URL fragment, remove it from browser history, and use a request header on API calls. Reject unexpected Host/Origin values; omit cross-origin allowances, deny unauthenticated API reads and writes, and accept JSON-only mutation requests. Serve assets only from the fixed build root with canonical containment checks. Restrict configuration destinations, reject links/reparse-point escapes in their parent chain and file, bound request size, and avoid recording tokens or full user file contents in errors. The service is local tooling, not a remotely deployable server.

Saves use a loaded revision/hash (including a missing-file sentinel), validation, and a same-directory temporary file followed by atomic replacement. A per-destination exclusive lock recording owner PID/start time and recheck prevent two editor processes from accepting the same stale revision; return a conflict for a changed file and keep the draft. Reject a locked destination with a recovery message rather than forcibly deleting a possibly active lock. Arbitrary external editors cannot honor that lock; document the remaining small race with non-cooperating writers rather than claiming filesystem compare-and-swap. Preserve old bytes on failed writes and clean owned temporary files.

Alternative: browser localStorage would not configure Codex, import/export-only would require extra manual file placement, and a Node backend would add a runtime requirement to the existing Python bundle.

### 6. User flow and installation

Use a scope selector (Global / Selected project), five interaction rows, expandable native specialist overrides, and a preview panel. Model controls accept custom exact IDs and preserve unknown saved IDs; those models can use Fixed, or Adaptive after a complete profile is supplied. Each row displays effective model, Fixed/Adaptive, effort or maximum, and inheritance source. Advanced settings expose the four-tier model maps. Display active destination, unsaved state, per-field errors, and explicit save/reset actions; project reset removes overrides. Temporary preview session overrides never persist. Show save conflicts with reload and draft-preservation options.

Keep the editor build optional. Both Wrangler scripts copy resolver/default data with the one visible skill. They copy built assets when present and clearly report editor unavailability when absent; they never run npm, install dependencies, build, start servers, or initialize/overwrite preference files. If no build is present on upgrade, remove only package-owned stale editor assets using verified paths so an older UI cannot masquerade as compatible. Use asset/policy compatibility metadata to reject mismatched builds. Ordinary native orchestration gains a new Python 3.10+ prerequisite (already required for Claude review), but not Node. Missing Python blocks routing with an actionable prerequisite message even when no preferences exist; do not silently use Markdown defaults. Document this explicitly.

### 7. Portable source-checkout launcher

The approved follow-up adds a dependency-free `scripts/editor.mjs` and root npm aliases `editor`, `editor:dev`, and `editor:build`. The script resolves paths relative to itself, uses argument arrays without a shell, discovers Python 3.10+ (with an explicit `CLANKER_PYTHON` executable override), and reports missing prerequisites. The nested editor package keeps dependency ownership. Built and development modes require an initial compatible editor build; no new Python API-only mode is introduced.

Normal mode starts the existing Python server. Development mode also runs Vite programmatically on loopback for hot reload, forwarding only API paths to the verified Python origin. Before translating Host/Origin headers, the proxy validates the incoming Vite Host, exact Origin for writes, and existing session token; it never adds authorization for an unauthenticated caller. Startup waits for readiness, prints one bootstrap URL, and cleans owned resources on failure, termination, or IPC-parent disconnect. The Python-only installed runtime and its security checks remain unchanged. Node is required only for these optional source-checkout commands and building/development.

## Risks / Trade-offs

- Heuristic effort mappings may be suboptimal -> label them provisional, make them editable, and record decisions for manual evaluation; do not infer stronger-model equivalence.
- A local editor cannot discover another Codex session's model catalog -> show unverified preview status and require runtime validation at dispatch.
- Layered inheritance can surprise users -> expose field sources and test project interaction versus global specialist precedence explicitly.
- A new local server expands filesystem access -> fixed destinations, loopback binding, session authentication, origin/host checks, and save-conflict tests bound it.
- Optional build assets can drift from Python policy -> version the contract, test parity, and reject incompatible assets.
- Some users only use native workers without Python today -> disclose the new runtime prerequisite and report it if absent; do not silently ignore preferences.

## Migration Plan

1. Add versioned defaults, resolver, and focused tests while keeping current model defaults and cross-review boundaries.
2. Integrate coordinator routing and provenance, then add the optional editor and local server.
3. Update both installers and test fresh, repeated, and upgraded installations with temporary roots and preference files.
4. Document editor build/start, preference precedence, provisional Adaptive maps, runtime limitations, and direct-launcher compatibility.
5. Validate on Windows and a supported Unix environment, inspect the running UI, and perform plan/implementation reviews through the established workflow when implementing this substantial change. Live subscription checks must remain separately reported from deterministic tests.
6. Roll back by reinstalling a prior bundle and retaining preferences for later reuse; the prior version ignores the new routing files. Within the new version, remove overrides to regain defaults. Never overwrite user preferences during rollback.
