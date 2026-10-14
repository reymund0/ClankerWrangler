#!/usr/bin/env bash
set -euo pipefail

CLAUDE_ROOT="${CLAUDE_ROOT:-$HOME/.claude}"
CODEX_ROOT="${CODEX_ROOT:-$HOME/.codex}"
WINDSURF_MEMORIES_ROOT="${WINDSURF_MEMORIES_ROOT:-$HOME/.codeium/windsurf/memories}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SOURCE="$REPO_ROOT/skills"
LEGACY_SKILLS_SOURCE="$SKILLS_SOURCE/legacy"
SUBAGENTS_SOURCE="$REPO_ROOT/subagents"
ORCHESTRATION_NAME="clanker-orchestration-nation"
GLOBAL_RULES_SOURCE="$REPO_ROOT/global_rules.md"
CROSS_REVIEW_LAUNCHER_SOURCE="$SUBAGENTS_SOURCE/scripts/claude_cross_review.py"
CROSS_REVIEW_CORE_SOURCE="$SUBAGENTS_SOURCE/scripts/cross_review_core.py"
CODEX_REVIEW_LAUNCHER_SOURCE="$SUBAGENTS_SOURCE/scripts/codex_cross_review.py"
HOSTS_SOURCE="$SUBAGENTS_SOURCE/hosts"
CLAUDE_WORKER_NAME="clanker-orchestration-worker"
CLAUDE_WORKER_SOURCE="$SUBAGENTS_SOURCE/claude/$CLAUDE_WORKER_NAME.md"
CLAUDE_WORKER_MARKER="<!-- clanker-orchestration-nation: managed worker definition -->"
ROUTING_POLICY_SOURCE="$SUBAGENTS_SOURCE/scripts/routing_policy.py"
ROUTING_EDITOR_SOURCE="$REPO_ROOT/routing-editor/scripts/routing_editor.py"
MODEL_DISCOVERY_SOURCE="$REPO_ROOT/routing-editor/scripts/model_discovery.py"
ROUTING_DATA_SOURCE="$SUBAGENTS_SOURCE/routing"
ROUTING_EDITOR_DIST_SOURCE="$REPO_ROOT/routing-editor/dist"
RETIRED_SPECIALISTS=(clanker-ux-designer clanker-documentation-writer clanker-product-engineer)
# References replaced by another file; only the installed reference is retired, never a standalone skill.
RETIRED_REFERENCES=(clanker-claude-cross-review)

copy_safe_file() {
    local dest="$1"
    local src="$2"

    if [[ -L "$dest" ]]; then
        rm -f "$dest"
    elif [[ -d "$dest" ]]; then
        echo "Error: Cannot replace directory with file: $dest" >&2
        exit 1
    fi

    mkdir -p "$(dirname "$dest")"
    cp -f "$src" "$dest"
    echo "Copied: $dest <- $src"
}

assert_safe_bundle_path() {
    local root="$1"
    local path="$2"
    local description="$3"
    local root_abs path_abs current relative part
    # Callers use the already canonical absolute agent root and literal descendants.
    # Avoid GNU-only realpath flags so the installer remains usable on macOS.
    root_abs="${root%/}"
    path_abs="$path"
    case "$root_abs" in /*) ;; *) echo "Error: Bundle root must be absolute" >&2; exit 1 ;; esac
    case "/$path_abs/" in */../*|*/./*) echo "Error: Invalid $description path" >&2; exit 1 ;; esac
    case "$path_abs" in "$root_abs"|"$root_abs"/*) ;; *) echo "Error: $description must remain within $root_abs: $path_abs" >&2; exit 1 ;; esac
    current="$root_abs"
    [[ ! -L "$current" ]] || { echo "Error: Cannot install through linked $description root: $current" >&2; exit 1; }
    relative="${path_abs#"$root_abs"/}"
    IFS='/' read -r -a parts <<< "$relative"
    for part in "${parts[@]}"; do
        [[ -z "$part" ]] && continue
        current="$current/$part"
        [[ ! -L "$current" ]] || { echo "Error: Cannot install through linked $description path: $current" >&2; exit 1; }
    done
    printf '%s\n' "$path_abs"
}

remove_routing_editor_assets() {
    local editor_dir="$1"
    local bundle_dir="$2"
    local name asset
    for name in index.html compatibility.json assets; do
        asset="$(assert_safe_bundle_path "$bundle_dir" "$editor_dir/$name" "routing editor")"
        [[ -e "$asset" || -L "$asset" ]] || continue
        rm -rf -- "$asset"
        echo "Removed packaged routing editor asset: $asset"
    done
}

copy_routing_directory() {
    local source_dir="$1"
    local destination_dir="$2"
    local bundle_dir="$3"
    local description="$4"
    local source relative destination
    while IFS= read -r -d '' source; do
        relative="${source#"$source_dir"/}"
        destination="$(assert_safe_bundle_path "$bundle_dir" "$destination_dir/$relative" "$description")"
        copy_safe_file "$destination" "$source"
    done < <(find "$source_dir" -type f ! -name "*.pyc" ! -path "*/__pycache__/*" -print0 | sort -z)
}

to_skill_display_name() {
    local skill_name="$1"
    local acronyms=("API" "CI" "CLI" "MCP" "PR" "UI")
    local small_words=("and" "or" "to" "up" "with")

    IFS='-' read -ra words <<< "$skill_name"
    local result=()
    local i=0

    for word in "${words[@]}"; do
        [[ -z "$word" ]] && continue

        local upper
        upper="$(echo "$word" | tr '[:lower:]' '[:upper:]')"
        local lower
        lower="$(echo "$word" | tr '[:upper:]' '[:lower:]')"
        local matched_acronym=false
        local matched_small=false

        for acr in "${acronyms[@]}"; do
            if [[ "$upper" == "$acr" ]]; then
                result+=("$upper")
                matched_acronym=true
                break
            fi
        done

        if ! $matched_acronym; then
            if [[ $i -gt 0 ]]; then
                for sw in "${small_words[@]}"; do
                    if [[ "$lower" == "$sw" ]]; then
                        result+=("$lower")
                        matched_small=true
                        break
                    fi
                done
            fi

            if ! $matched_small; then
                result+=("${upper:0:1}${lower:1}")
            fi
        fi

        (( i++ )) || true
    done

    local IFS=" "
    echo "${result[*]}"
}

to_yaml_quoted_string() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    value="${value//$'\n'/\\n}"
    echo "\"$value\""
}

new_codex_openai_yaml() {
    local skill_dir="$1"
    local skill_name="$2"

    local agents_dir="$skill_dir/agents"
    local openai_yaml="$agents_dir/openai.yaml"
    local display_name
    display_name="$(to_skill_display_name "$skill_name")"

    local short_description="Help with $display_name workflows"
    if [[ ${#short_description} -gt 64 ]]; then
        short_description="$display_name helper"
    fi

    local default_prompt="Use \$$skill_name to help with this task."

    mkdir -p "$agents_dir"

    cat > "$openai_yaml" <<EOF
interface:
  display_name: $(to_yaml_quoted_string "$display_name")
  short_description: $(to_yaml_quoted_string "$short_description")
  default_prompt: $(to_yaml_quoted_string "$default_prompt")

policy:
  allow_implicit_invocation: true

EOF
    echo "Generated: $openai_yaml"
}

remove_legacy_skills() {
    local agent_skills_root="$1"

    if [[ ! -d "$LEGACY_SKILLS_SOURCE" ]]; then
        return
    fi

    while IFS= read -r -d '' legacy_file; do
        local base
        base="$(basename "$legacy_file")"
        local skill_name="${base%.md}"
        local skill_dir="$agent_skills_root/$skill_name"

        if [[ -d "$skill_dir" ]]; then
            rm -rf "$skill_dir"
            echo "Removed legacy skill: $skill_dir"
        fi
    done < <(find "$LEGACY_SKILLS_SOURCE" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)
}

preflight_retired_specialists() {
    local agent_root="$1"
    local references="$agent_root/skills/$ORCHESTRATION_NAME/references"
    local name source backup have_entries=false
    assert_safe_bundle_path "$agent_root" "$references" "specialist references" >/dev/null
    for name in "${RETIRED_SPECIALISTS[@]}"; do
        for source in "$references/$name.md" "$agent_root/skills/$name"; do
            assert_safe_bundle_path "$agent_root" "$source" "retired specialist" >/dev/null
            [[ -e "$source" ]] || continue
            if [[ "$source" == "$references/"* ]]; then
                [[ -f "$source" ]] || { echo "Error: Unexpected retired specialist entry type: $source" >&2; exit 1; }
            else
                [[ -d "$source" ]] || { echo "Error: Unexpected retired specialist entry type: $source" >&2; exit 1; }
            fi
            have_entries=true
        done
    done
    for name in "${RETIRED_REFERENCES[@]}"; do
        source="$references/$name.md"
        assert_safe_bundle_path "$agent_root" "$source" "retired reference" >/dev/null
        [[ -e "$source" ]] || continue
        [[ -f "$source" ]] || { echo "Error: Unexpected retired reference entry type: $source" >&2; exit 1; }
        have_entries=true
    done
    if "$have_entries"; then
        for backup in "$agent_root/backups" "$agent_root/backups/orchestration-nation"; do
            assert_safe_bundle_path "$agent_root" "$backup" "retirement backup" >/dev/null
            [[ ! -e "$backup" || -d "$backup" ]] || { echo "Error: Backup destination is not a directory: $backup" >&2; exit 1; }
        done
    fi
}

move_retired_entry() {
    local agent_root="$1"
    local source="$2"
    local name="$3"
    local extension="$4"
    local backup_root="$agent_root/backups/orchestration-nation"
    local destination suffix
    assert_safe_bundle_path "$agent_root" "$source" "retired specialist" >/dev/null
    [[ -e "$source" ]] || return 0
    assert_safe_bundle_path "$agent_root" "$backup_root" "retirement backup" >/dev/null
    mkdir -p "$backup_root"
    destination="$backup_root/$name$extension"
    suffix=2
    while [[ -e "$destination" || -L "$destination" ]]; do
        destination="$backup_root/$name-$suffix$extension"
        suffix=$((suffix + 1))
    done
    assert_safe_bundle_path "$agent_root" "$destination" "retirement backup" >/dev/null
    mv -n "$source" "$destination"
    [[ ! -e "$source" ]] || { echo "Error: Retirement move did not complete: $source -> $destination" >&2; exit 1; }
    echo "Moved retired specialist to backup: $source -> $destination"
}

retire_specialists() {
    local agent_root="$1"
    local references="$agent_root/skills/$ORCHESTRATION_NAME/references"
    local name
    for name in "${RETIRED_SPECIALISTS[@]}"; do
        move_retired_entry "$agent_root" "$references/$name.md" "$name" ".md"
        move_retired_entry "$agent_root" "$agent_root/skills/$name" "$name" ""
    done
    for name in "${RETIRED_REFERENCES[@]}"; do
        move_retired_entry "$agent_root" "$references/$name.md" "$name" ".md"
    done
}

# The generic Claude worker lives in <claude-root>/agents. Preflight it before any write so a
# linked agents directory or an unexpected entry stops the install untouched.
preflight_claude_worker() {
    local agent_root="$1"
    local agents_dir="$agent_root/agents"
    local destination="$agents_dir/$CLAUDE_WORKER_NAME.md"
    local backup
    assert_safe_bundle_path "$agent_root" "$agents_dir" "agent definitions" >/dev/null
    assert_safe_bundle_path "$agent_root" "$destination" "worker definition" >/dev/null
    [[ ! -e "$agents_dir" || -d "$agents_dir" ]] || { echo "Error: Agent definitions path is not a directory: $agents_dir" >&2; exit 1; }
    [[ -e "$destination" ]] || return 0
    [[ -f "$destination" ]] || { echo "Error: Unexpected worker definition entry type: $destination" >&2; exit 1; }
    if ! grep -qF -- "$CLAUDE_WORKER_MARKER" "$destination"; then
        for backup in "$agent_root/backups" "$agent_root/backups/orchestration-nation"; do
            assert_safe_bundle_path "$agent_root" "$backup" "worker definition backup" >/dev/null
            [[ ! -e "$backup" || -d "$backup" ]] || { echo "Error: Backup destination is not a directory: $backup" >&2; exit 1; }
        done
    fi
}

install_claude_worker() {
    local agent_root="$1"
    local agents_dir="$agent_root/agents"
    local destination="$agents_dir/$CLAUDE_WORKER_NAME.md"
    local backup_root="$agent_root/backups/orchestration-nation"
    local backup suffix
    preflight_claude_worker "$agent_root"
    mkdir -p "$agents_dir"
    if [[ -f "$destination" ]] && ! grep -qF -- "$CLAUDE_WORKER_MARKER" "$destination"; then
        mkdir -p "$backup_root"
        backup="$backup_root/$CLAUDE_WORKER_NAME.md"
        suffix=2
        while [[ -e "$backup" || -L "$backup" ]]; do
            backup="$backup_root/$CLAUDE_WORKER_NAME-$suffix.md"
            suffix=$((suffix + 1))
        done
        assert_safe_bundle_path "$agent_root" "$backup" "worker definition backup" >/dev/null
        mv -n "$destination" "$backup"
        [[ ! -e "$destination" ]] || { echo "Error: Worker definition backup did not complete: $destination -> $backup" >&2; exit 1; }
        echo "Moved unmanaged worker definition to backup: $destination -> $backup"
    fi
    copy_safe_file "$destination" "$CLAUDE_WORKER_SOURCE"
}

host_directory_for() {
    case "$1" in
        "Claude Code") echo "claude" ;;
        "Codex") echo "codex" ;;
        *) echo "Error: Unknown orchestration host for $1" >&2; exit 1 ;;
    esac
}

install_orchestration_bundle() {
    local agent_name="$1"
    local agent_root
    agent_root="$(cd "$2" && pwd -P)"
    local agent_skills_root="$agent_root/skills"
    local bundle_dir="$agent_skills_root/$ORCHESTRATION_NAME"
    local references_dir="$bundle_dir/references"
    local host_name
    host_name="$(host_directory_for "$agent_name")"
    assert_safe_bundle_path "$agent_root" "$bundle_dir" "orchestration bundle" >/dev/null
    preflight_retired_specialists "$agent_root"
    if [[ "$agent_name" == "Claude Code" ]]; then
        preflight_claude_worker "$agent_root"
    fi

    copy_safe_file "$bundle_dir/SKILL.md" "$SUBAGENTS_SOURCE/$ORCHESTRATION_NAME.md"
    while IFS= read -r -d '' specialist; do
        local base
        base="$(basename "$specialist")"
        [[ "$base" == "$ORCHESTRATION_NAME.md" ]] && continue
        copy_safe_file "$references_dir/$base" "$specialist"
    done < <(find "$SUBAGENTS_SOURCE" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)
    copy_safe_file "$references_dir/host.md" "$HOSTS_SOURCE/$host_name/host.md"
    if [[ -L "$bundle_dir/scripts" ]]; then
        echo "Error: Cannot install through a linked scripts directory: $bundle_dir/scripts" >&2
        exit 1
    fi
    copy_safe_file "$bundle_dir/scripts/cross_review_core.py" "$CROSS_REVIEW_CORE_SOURCE"
    copy_safe_file "$bundle_dir/scripts/claude_cross_review.py" "$CROSS_REVIEW_LAUNCHER_SOURCE"
    copy_safe_file "$bundle_dir/scripts/codex_cross_review.py" "$CODEX_REVIEW_LAUNCHER_SOURCE"
    local policy_destination editor_destination discovery_destination
    policy_destination="$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/routing_policy.py" "routing scripts")"
    editor_destination="$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/routing_editor.py" "routing scripts")"
    copy_safe_file "$policy_destination" "$ROUTING_POLICY_SOURCE"
    copy_safe_file "$editor_destination" "$ROUTING_EDITOR_SOURCE"
    discovery_destination="$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/model_discovery.py" "routing scripts")"
    copy_safe_file "$discovery_destination" "$MODEL_DISCOVERY_SOURCE"
    copy_routing_directory "$ROUTING_DATA_SOURCE" "$bundle_dir/routing" "$bundle_dir" "routing data"
    copy_safe_file "$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/routing/host.json" "host configuration")" "$HOSTS_SOURCE/$host_name/host.json"

    local editor_dir="$bundle_dir/editor"
    remove_routing_editor_assets "$editor_dir" "$bundle_dir"
    if [[ -d "$ROUTING_EDITOR_DIST_SOURCE" ]]; then
        if [[ ! -f "$ROUTING_EDITOR_DIST_SOURCE/compatibility.json" ]]; then
            echo "Error: Routing editor build is missing compatibility.json: $ROUTING_EDITOR_DIST_SOURCE" >&2
            exit 1
        fi
        copy_routing_directory "$ROUTING_EDITOR_DIST_SOURCE" "$editor_dir" "$bundle_dir" "routing editor"
    else
        echo "Routing editor build unavailable; installed routing helpers without editor assets."
    fi
    if [[ "$agent_name" == "Codex" ]]; then
        new_codex_openai_yaml "$bundle_dir" "$ORCHESTRATION_NAME"
    fi
    retire_specialists "$agent_root"
    if [[ "$agent_name" == "Claude Code" ]]; then
        install_claude_worker "$agent_root"
    fi

    # Preserve old standalone entries outside skill discovery after the bundle is ready.
    local backup_base="$agent_root/backups"
    local backup_root="$backup_base/orchestration-nation"
    while IFS= read -r -d '' specialist; do
        local base
        base="$(basename "$specialist")"
        [[ "$base" == "$ORCHESTRATION_NAME.md" ]] && continue
        local name="${base%.md}"
        local standalone_dir="$agent_skills_root/$name"
        [[ -e "$standalone_dir" || -L "$standalone_dir" ]] || continue
        if [[ ! -d "$standalone_dir" && ! -L "$standalone_dir" ]]; then
            echo "Error: Cannot migrate non-directory specialist entry: $standalone_dir" >&2
            exit 1
        fi
        if [[ -L "$backup_base" || -L "$backup_root" ]]; then
            echo "Error: Cannot migrate through a linked backup directory: $backup_root" >&2
            exit 1
        fi
        mkdir -p "$backup_root"
        local backup_dir="$backup_root/$name"
        local suffix=2
        while [[ -e "$backup_dir" || -L "$backup_dir" ]]; do
            backup_dir="$backup_root/$name-$suffix"
            suffix=$((suffix + 1))
        done
        case "$standalone_dir" in "$agent_skills_root/"*) ;; *) exit 1 ;; esac
        case "$backup_dir" in "$backup_root/"*) ;; *) exit 1 ;; esac
        mv "$standalone_dir" "$backup_dir"
        echo "Moved standalone specialist skill to backup: $standalone_dir -> $backup_dir"
    done < <(find "$SUBAGENTS_SOURCE" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)
}

install_agent_links() {
    local agent_name="$1"
    local agent_root="$2"
    local rules_file_name="$3"

    local agent_skills_root="$agent_root/skills"
    local rules_link="$agent_root/$rules_file_name"

    echo "Configuring $agent_name at $agent_root"

    mkdir -p "$agent_root"
    agent_root="$(cd "$agent_root" && pwd -P)"
    agent_skills_root="$agent_root/skills"
    rules_link="$agent_root/$rules_file_name"
    preflight_retired_specialists "$agent_root"
    if [[ "$agent_name" == "Claude Code" ]]; then
        preflight_claude_worker "$agent_root"
    fi
    mkdir -p "$agent_skills_root"

    remove_legacy_skills "$agent_skills_root"

    while IFS= read -r -d '' skill_file; do
        local base
        base="$(basename "$skill_file")"
        local skill_name="${base%.md}"
        local skill_dir="$agent_skills_root/$skill_name"
        local skill_link="$skill_dir/SKILL.md"

        mkdir -p "$skill_dir"
        copy_safe_file "$skill_link" "$skill_file"

        if [[ "$agent_name" == "Codex" ]]; then
            new_codex_openai_yaml "$skill_dir" "$skill_name"
        fi
    done < <(find "$SKILLS_SOURCE" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)

    install_orchestration_bundle "$agent_name" "$agent_root"

    copy_safe_file "$rules_link" "$GLOBAL_RULES_SOURCE"
}

install_windsurf_rules() {
    local memories_root="$1"
    local rules_link="$memories_root/global_rules.md"

    echo "Configuring Windsurf memories at $memories_root"

    mkdir -p "$memories_root"
    copy_safe_file "$rules_link" "$GLOBAL_RULES_SOURCE"
}

if [[ ! -d "$SKILLS_SOURCE" ]]; then
    echo "Error: Skills source directory not found: $SKILLS_SOURCE" >&2
    exit 1
fi

if [[ ! -d "$SUBAGENTS_SOURCE" || ! -f "$SUBAGENTS_SOURCE/$ORCHESTRATION_NAME.md" ]]; then
    echo "Error: Orchestration source directory or coordinator not found: $SUBAGENTS_SOURCE" >&2
    exit 1
fi

if [[ ! -f "$GLOBAL_RULES_SOURCE" ]]; then
    echo "Error: Global rules file not found: $GLOBAL_RULES_SOURCE" >&2
    exit 1
fi

if [[ ! -f "$CROSS_REVIEW_LAUNCHER_SOURCE" ]]; then
    echo "Error: Claude cross-review launcher not found: $CROSS_REVIEW_LAUNCHER_SOURCE" >&2
    exit 1
fi

for review_source in "$CROSS_REVIEW_CORE_SOURCE" "$CODEX_REVIEW_LAUNCHER_SOURCE" "$CLAUDE_WORKER_SOURCE" \
    "$HOSTS_SOURCE/claude/host.md" "$HOSTS_SOURCE/claude/host.json" "$HOSTS_SOURCE/codex/host.md" "$HOSTS_SOURCE/codex/host.json"; do
    if [[ ! -f "$review_source" ]]; then
        echo "Error: Orchestration host or review source file not found: $review_source" >&2
        exit 1
    fi
done

for routing_source in "$ROUTING_POLICY_SOURCE" "$ROUTING_EDITOR_SOURCE" "$MODEL_DISCOVERY_SOURCE"; do
    if [[ ! -f "$routing_source" ]]; then
        echo "Error: Routing helper source file not found: $routing_source" >&2
        exit 1
    fi
done
if [[ ! -d "$ROUTING_DATA_SOURCE" ]]; then
    echo "Error: Routing data source directory not found: $ROUTING_DATA_SOURCE" >&2
    exit 1
fi

install_agent_links "Claude Code" "$CLAUDE_ROOT" "CLAUDE.md"
install_agent_links "Codex" "$CODEX_ROOT" "AGENTS.md"
install_windsurf_rules "$WINDSURF_MEMORIES_ROOT"
