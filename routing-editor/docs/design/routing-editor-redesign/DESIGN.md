# Routing editor redesign: design handoff

Source canvas (private, owner only): https://claude.ai/artifact/SEFWqNDaToEhCDNaFtYSVP

This redesign replaces the single long scrolling page in `routing-editor/src/App.tsx` with four
tabbed screens, in light and dark themes. The board files in `boards/` are the visual spec.
They are HTML with inline styles but depend on the Claude Design runtime (`support.js`, `<x-dc>`,
`<sc-for>`, `{{holes}}`), so read them as reference; don't open or ship them as-is.

## Scope and constraints

- UI only. Do not change the Python API (`routing-editor/scripts/routing_editor.py`), the routing
  policy, the preference file format or any save, validation or conflict behavior.
- Keep every existing capability: scope switching with the unsaved-draft confirm, save with
  revision and conflict handling, export draft and reload, reset scope override, Run Wrangler
  and its install details, model catalog refresh, field-level errors, the session override
  in preview, and the "Varies by activity" and "saved; unavailable for new selection" states.
- Keep accessibility at least at today's level: real labels, `aria-describedby` to help and
  error text, `aria-live` status, and focus-visible outlines. Touch targets should be at least 40px.
- No new dependencies. Use plain CSS in `styles.css` with custom properties for the themes.
- The mockup data is **sample data**: the agent-to-activity mapping, the overrides (Backend
  developer → `gpt-6-astra`, Documentation writer → `gpt-5.6-luna`, Visual & UX review set
  here, the customized `gpt-5.6-sol` profile) and the `[N]`/`[TIME]` catalog placeholders.
  Real values come from `/api` responses exactly as they do today (for example
  `specialistChoices`, `config.effective` and `catalog`).

## Boards

| File | Screen |
| --- | --- |
| `boards/Main.dc.html` / `MainDark.dc.html` | Worker routes: agent × activity matrix plus inspector |
| `boards/ActivityDefaults.dc.html` / `…Dark` | Activity defaults |
| `boards/AdaptiveProfiles.dc.html` / `…Dark` | Adaptive profiles |
| `boards/RouteTrace.dc.html` / `…Dark` | Preview a route |
| `boards/Current.dc.html` | The current UI, recreated for comparison |

Frames are 1440 px wide. Responsive behavior isn't drawn. Keep today's breakpoints in spirit:
the matrix scrolls horizontally, and the inspector stacks below it under about 1100 px.

## App shell (all screens)

1. **Header bar (68px, dark in both themes).** It contains:
   - "Orchestration Nation · Routing" wordmark
   - scope segmented control (Global / Project · name; Project is disabled when unavailable)
   - scope file path in monospace
   - save-state pill (amber "N unsaved changes" or neutral "All changes saved", `aria-live`)
   - buttons: Run Wrangler, Export draft & reload, and a primary "Save {scope}"
2. **Section tabs (48px).** Worker routes · Activity defaults · Adaptive profiles · Preview a
   route. These are client-side tabs with no router dependency; keep the tab in state and
   optionally mirror it in the URL hash. The draft, scope and errors are shared across tabs.
   Show a small error dot on any tab that has field errors, replacing today's
   auto-expand-on-error behavior.
3. **Alerts.** `errors.save`, `errors.validation`, `errors.preview` and `errors.load` render
   under the tabs as a dismissible banner, instead of in the fixed footer.
4. The fixed bottom action footer is removed; its actions move to the header.
5. The Run Wrangler install details and output move into a popover anchored to the button.

## Screen 1: Worker routes (`Main`)

Replaces `CatalogStatusPanel`, the `AgentCard` grid and the Claude `InteractionCard`.

- **Title row:** "Worker routes", a one-line description, and a legend (Inherited / Set in
  this scope / Activity exception).
- **Catalog strip:** one line per provider with a status dot, `{status} via {source}
  {cli_version} · updated {updated_at}`, any error, and a Refresh models button. This is
  `CatalogStatusPanel`, restyled.
- **Matrix** (`role="table"`):
  - Columns: Specialist, Agent default, then one column per Codex activity from
    `config.bundle.interactions`.
  - Rows: one per `config.bundle.roles`. The row header shows an "N exceptions" pill when
    activity exceptions exist (same count as today's `exception-note`).
  - Each cell is a button showing the model id (monospace) and the effort summary
    (`adaptive ≤ {ceiling}` or `fixed · {effort}`).
  - Cell state, in the colors below:
    - `inherited`: the value comes from a lower layer
    - `set`: the agent default is set in this scope
    - `exception`: an activity-specific route is set for this agent
    - `varies`: dashed amber, agent default only, when the activity values differ
    - `not used`: the role isn't in `specialistChoices` for that activity
  - Clicking a row or cell selects that agent for the inspector.
  - A final row holds the Claude cross-review route: model, effort summary, and the
    "alias · resolution may change" pill when `isClaudeAlias`.
- **Inspector** (right panel, 400px) for the selected agent. It replaces the `AgentCard` body:
  - name and role id
  - Agent default block: model picker with a "From: {provenance}" line, an Adaptive / Fixed
    segmented control, effort or Adaptive maximum, and Reset agent default. Field-level reset
    stays reachable next to each field or in a menu.
  - By activity: one row per activity the agent takes part in, showing its value and state tag.
    Selecting an exception row expands its `RouteEditor` inline with Reset activity exception.
    "+ Add activity exception" opens the editor for an activity with no exception yet.
  - Footer button: "Preview a decision for this agent", which switches to the Preview tab with
    the activity and agent prefilled.
  - When the Claude row is selected, the inspector shows the `claude-review` `RouteEditor`
    and Reset route to inherited.

## Screen 2: Activity defaults (`ActivityDefaults`)

Replaces `AdvancedActivityDefaults`; it's no longer collapsed.

- A precedence strip at the top: Bundled defaults → **Activity default** → Agent default →
  Activity exception.
- A 2×2 grid with one card per Codex interaction. Each card has:
  - name, id, a Set here / Inherited tag, and a provider badge
  - "Used by N:" chips listing the specialists for that interaction (from `specialistChoices`)
  - model picker, Adaptive / Fixed segmented control, effort or Adaptive maximum, and the
    ceiling note
  - Reset model, Reset reasoning, and Reset route to inherited, disabled when nothing is set
    in this scope
- A card with an own route gets the teal border.

## Screen 3: Adaptive profiles (`AdaptiveProfiles`)

Replaces `AdvancedProfiles`; it's no longer collapsed.

- **Add bar:** Provider segmented control (Codex / Claude), a model select (locally reported
  models only; disabled with a message when there are none), and "Customize profile". This is
  today's `createProfile`.
- **Family accordions:** the table's rows are grouped into collapsible sections, one per
  model family, all inside the one table so the columns stay aligned.
  - Codex families come from the version in the model id: `gpt-5.6-*` → "5.6", `gpt-6-*` →
    "6", `gpt-6.1-*` → "6.1". Derive them from the row keys (don't hard-code them) and sort
    by version descending (newest first), so `gpt-5.5` gets its own "5.5" section and a future `gpt-6.2-*` appears on
    its own. A Codex id that doesn't match goes in an "Other" section, shown only when needed.
    All Claude rows go in one "Claude · Models" section, first; "Other" stays last.
  - Each section header is a full-width `<button aria-expanded>` with a chevron, the
    provider, the family name, "N models", and "· N customized here" when any row in it is
    overridden in this scope.
  - Sections start expanded when they contain a customized row or a field error, and
    collapsed otherwise. A field error inside a collapsed section expands it.
  - Keep the open/closed state in component state only; don't save it.
- **Table:** one row per model, showing both bundled/effective profiles
  (`config.effective.profiles`) and profiles overridden in this scope.
  - Columns: Mechanical, Routine, Complex, Exceptional, Default ceiling.
  - Each cell shows the effort plus a meter with **one bar per effort that can be selected for
    that row's model**, which is the same list its select offers (`effortChoices` options that
    aren't disabled, in `effort_orders` order). A model that allows low–max gets 5 bars; one
    that allows minimal–ultra gets 7. Leave out the extra "(saved; unavailable for new
    selection)" option, but if the current value is such a saved-unavailable effort, add
    it as one more bar at its place in the order.
  - Bars up to and including the current effort are filled. Each filled bar takes its
    **own level's color**, so the meter reads as a ramp, and a given effort is always the
    same color everywhere. Bars above it use the empty color.

    | Level | Light | Dark |
    | --- | --- | --- |
    | `none`/`minimal` | `#9AA0A8` | `#80848D` |
    | `low` | `#2F9C8C` | `#4CC3B3` |
    | `medium` | `#3B78D0` | `#6AA3F0` |
    | `high` | `#C29A1F` | `#E3C04F` |
    | `xhigh` | `#DB7429` | `#F2974F` |
    | `max` | `#C8423A` | `#F06A5E` |
    | `ultra` | `#8450C8` | `#B287F0` |
    | empty | `#E7E5DE` | `#2E3138` |

    Add these as `--effort-*` tokens in `styles.css`. The meter stays `aria-hidden`, because
    the effort text next to it carries the value, so color never carries meaning alone.
    Changed cells keep their accent border and fill; the meter no longer shows change.
  - Rows overridden in this scope are editable: each cell is a select using `effortChoices`.
    They get a teal left bar and teal cells where they differ from the inherited profile,
    plus Reset profile.
  - Inherited rows are read-only, with a Customize button that creates the override (the same
    as adding the profile).
- **Example line:** under the table, the first customized row works through a complex task:
  tier → profile effort → ceiling → requested effort. Compute it client-side from the table
  data; do not call `/preview` for it.
- **Footnote:** only efforts the CLI reports can be chosen, and profiles are policy, not a
  quality guarantee.

## Screen 4: Preview a route (`RouteTrace`)

Replaces `Preview`.

- **Left form (420px):**
  - Activity and Specialist (optional) selects
  - task tier as a four-way segmented control
  - risk flags as toggle chips (`aria-pressed`)
  - Reason input (required)
  - Temporary session override in a `<details>` (model, mode, effort, as today)
  - a primary Preview route button
  - an intro line saying it uses the unsaved draft and nothing is saved or run
- **Result hero:** the predicted model (large, monospace) and requested effort, plus
  Proposed, Ceiling and Capability (`decision.capability_status`).
- **"How it resolved" table:** the eight precedence layers, lowest to highest:
  1. Bundled defaults
  2. Global activity
  3. Global agent default
  4. Global activity exception
  5. Project activity
  6. Project agent default
  7. Project activity exception
  8. Session override

  Each layer has model and reasoning columns. The winning value in each column is highlighted
  teal with a "WINS" tag. Values it overrode are struck through, and empty layers show "—".
  - **Data gap:** `decision.provenance` names only the winning source per field. Filling the
    other layers needs either the per-layer values the client already has (the global and
    project documents plus the bundle defaults, resolved with the same precedence), or a small
    API addition. **Do not change the API without approval.** If it can't be derived
    client-side, ship with only the winning layers highlighted and the rest shown as "—".
- **"How effort was chosen":** tier (noting when a risk flag raised it), then the profile
  mapping, then the ceiling, then the requested effort. Use `decision` fields where they exist.
- **Limitations box:** list `decision.limitations`, plus the standing note that the catalog
  is not proof of runtime availability.

## Visual tokens

Fonts (Google Fonts): **Bricolage Grotesque** 600/700 for headings, **IBM Plex Sans**
400/500/600 for text, **JetBrains Mono** 400/500 for model ids and paths. This needs a
`<link>` in `routing-editor/index.html`. The app is local-first, so a system-font fallback
stack must look acceptable offline.

| Token | Light | Dark |
| --- | --- | --- |
| `--bg` page | `#F4F3EE` | `#121317` |
| `--surface` | `#FFFFFF` | `#1B1D22` |
| `--surface-2` (table header, subtle) | `#FAF9F6` | `#17191D` |
| `--raised` (inputs in dark, inherited cells) | `#FFFFFF` | `#22252B` |
| `--field-bg` | `#FFFFFF` | `#121317` |
| `--segment-bg` | `#ECEAE3` | `#15171B` |
| `--segment-active` | `#FFFFFF` | `#33363E` |
| `--line` | `#E2E0D8` | `#2E3138` |
| `--line-soft` (row dividers) | `#EFEDE6` | `#262930` |
| `--field-border` | `#C9C6BB` | `#3A3D45` |
| `--ink` | `#17191E` | `#ECEBE6` |
| `--ink-2` | `#3E424B` | `#C9CBD1` |
| `--muted` | `#5B5F68` | `#A7AAB2` |
| `--faint` (n/a, struck values) | `#8A8D95` | `#80848D` |
| `--header-bg` | `#17191E` | `#0B0C0F` |
| `--accent` (set here, primary, links) | `#0B6B6B` | `#3CC2B5` |
| `--accent-soft` | `#E3F1EF` | `#12302E` |
| `--accent-ink` | `#0A3D3D` | `#BFEDE7` |
| `--on-accent` | `#FFFFFF` | `#0B1F1E` |
| `--warn` (exception border) | `#C77A2E` | `#E0A25A` |
| `--warn-soft` | `#FBEEDC` | `#3A2A16` |
| `--warn-ink` | `#6B3708` | `#F5D3A6` |
| `--claude-soft` | `#F6F3FA` | `#1E1B26` |
| `--claude-ink` | `#4B3A6E` | `#CFC3EE` |
| `--ok` (catalog dot) | `#2F8F5B` | `#4CC38A` |
| `--error` | `#9C1C24` | `#FF8A8A` (not drawn; verify contrast) |

The header Save button uses `#2FA39A` on `#0B1F1E` text in light mode.
Radii: 7px for cells and inputs, 8–10px for controls, 12px for cards and tables, 999px for pills.
Theme: follow `prefers-color-scheme` by default and allow a manual override. A toggle
location isn't drawn yet; the header right side is suggested.

## Suggested implementation order

1. Add theme tokens to `styles.css` and apply them to the current layout (no structure change).
2. Build the app shell: header, tabs, and the error banner. Move the footer actions.
3. Move the existing `Preview`, `AdvancedActivityDefaults` and `AdvancedProfiles` into tabs
   unchanged, then restyle them into screens 2–4.
4. Build the matrix and inspector from the existing `AgentCard` logic. Extract the per-agent
   derivations (baseline, mixed, exceptions) into testable helpers first.
5. Update `App.test.tsx` and `discovery.test.tsx`: they query today's labels and buttons, and
   expanded sections, so many selectors will move.

Each step should keep the editor fully usable. Check both themes and at 375px width.
