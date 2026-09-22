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
ROUTING_POLICY_SOURCE="$SUBAGENTS_SOURCE/scripts/routing_policy.py"
ROUTING_EDITOR_SOURCE="$SUBAGENTS_SOURCE/scripts/routing_editor.py"
MODEL_DISCOVERY_SOURCE="$SUBAGENTS_SOURCE/scripts/model_discovery.py"
ROUTING_DATA_SOURCE="$SUBAGENTS_SOURCE/routing"
ROUTING_EDITOR_DIST_SOURCE="$REPO_ROOT/routing-editor/dist"

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

install_orchestration_bundle() {
    local agent_name="$1"
    local agent_root
    agent_root="$(cd "$2" && pwd -P)"
    local agent_skills_root="$agent_root/skills"
    local bundle_dir="$agent_skills_root/$ORCHESTRATION_NAME"
    local references_dir="$bundle_dir/references"
    assert_safe_bundle_path "$agent_root" "$bundle_dir" "orchestration bundle" >/dev/null

    copy_safe_file "$bundle_dir/SKILL.md" "$SUBAGENTS_SOURCE/$ORCHESTRATION_NAME.md"
    while IFS= read -r -d '' specialist; do
        local base
        base="$(basename "$specialist")"
        [[ "$base" == "$ORCHESTRATION_NAME.md" ]] && continue
        copy_safe_file "$references_dir/$base" "$specialist"
    done < <(find "$SUBAGENTS_SOURCE" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)
    if [[ -L "$bundle_dir/scripts" ]]; then
        echo "Error: Cannot install through a linked scripts directory: $bundle_dir/scripts" >&2
        exit 1
    fi
    copy_safe_file "$bundle_dir/scripts/claude_cross_review.py" "$CROSS_REVIEW_LAUNCHER_SOURCE"
    local policy_destination editor_destination discovery_destination
    policy_destination="$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/routing_policy.py" "routing scripts")"
    editor_destination="$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/routing_editor.py" "routing scripts")"
    copy_safe_file "$policy_destination" "$ROUTING_POLICY_SOURCE"
    copy_safe_file "$editor_destination" "$ROUTING_EDITOR_SOURCE"
    discovery_destination="$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/model_discovery.py" "routing scripts")"
    copy_safe_file "$discovery_destination" "$MODEL_DISCOVERY_SOURCE"
    copy_routing_directory "$ROUTING_DATA_SOURCE" "$bundle_dir/routing" "$bundle_dir" "routing data"

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
