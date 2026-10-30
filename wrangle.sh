#!/usr/bin/env bash
set -euo pipefail

CLAUDE_ROOT="${CLAUDE_ROOT:-$HOME/.claude}"
CODEX_ROOT="${CODEX_ROOT:-$HOME/.codex}"
WINDSURF_MEMORIES_ROOT="${WINDSURF_MEMORIES_ROOT:-$HOME/.codeium/windsurf/memories}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SOURCE="$REPO_ROOT/skills"
SUBAGENTS_SOURCE="$REPO_ROOT/subagents"
ORCHESTRATION_NAME="clanker-orchestration-nation"
GLOBAL_RULES_SOURCE="$REPO_ROOT/global_rules.md"
HOSTS_SOURCE="$SUBAGENTS_SOURCE/hosts"
DUAL_REVIEW_NAME="clanker-dual-review"
# The three role references; each also has an agent definition in subagents/claude/ (.md) and subagents/codex/ (.toml).
ROLE_NAMES=(clanker-implementor clanker-reviewer clanker-functional-review)
DUAL_REVIEW_SCRIPTS=(cross_review.py cross_review_codex.py cross_review_claude.py clanker_log.py)
REVIEWER_ROLE_SOURCE="$SUBAGENTS_SOURCE/clanker-reviewer.md"
# Installed names from earlier versions. The installer deletes each one that exists under an agent
# root, without backups, and prints it.
RETIRED_SKILLS=(clanker-plan-with-codex clanker-refactor-sisyphus clanker-refine-ticket-with-codex clanker-refine-ticket codex-review)
RETIRED_ROLE_NAMES=(clanker-architect clanker-backend-developer clanker-data-engineer clanker-devops-engineer
    clanker-performance-engineer clanker-qa-engineer clanker-test-engineer clanker-ui-developer clanker-ui-ux-reviewer
    clanker-ux-designer clanker-documentation-writer clanker-product-engineer clanker-cross-review clanker-claude-cross-review)
RETIRED_PATHS=(
    "skills/$ORCHESTRATION_NAME/scripts" "skills/$ORCHESTRATION_NAME/routing" "skills/$ORCHESTRATION_NAME/editor"
    agents/clanker-orchestration-worker.md backups/orchestration-nation
)

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

remove_retired_paths() {
    local agent_root="$1"
    local name relative path
    local paths=("${RETIRED_PATHS[@]}")
    for name in "${RETIRED_SKILLS[@]}" "${RETIRED_ROLE_NAMES[@]}"; do
        paths+=("skills/$name")
    done
    for name in "${RETIRED_ROLE_NAMES[@]}"; do
        paths+=("skills/$ORCHESTRATION_NAME/references/$name.md")
    done
    for relative in "${paths[@]}"; do
        path="$agent_root/$relative"
        # Check the parent so a linked retired entry is removed as a link, never followed.
        assert_safe_bundle_path "$agent_root" "$(dirname "$path")" "retired path" >/dev/null
        [[ -e "$path" || -L "$path" ]] || continue
        rm -rf -- "$path"
        echo "Removed retired path: $path"
    done
    # The old installer's backups folder goes too once it is empty.
    rmdir "$agent_root/backups" 2>/dev/null || true
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

    copy_safe_file "$bundle_dir/SKILL.md" "$SUBAGENTS_SOURCE/$ORCHESTRATION_NAME.md"
    local role
    for role in "${ROLE_NAMES[@]}"; do
        copy_safe_file "$(assert_safe_bundle_path "$bundle_dir" "$references_dir/$role.md" "role references")" \
            "$SUBAGENTS_SOURCE/$role.md"
    done
    copy_safe_file "$(assert_safe_bundle_path "$bundle_dir" "$references_dir/host.md" "host reference")" \
        "$HOSTS_SOURCE/$host_name/host.md"
    copy_safe_file "$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/host.json" "host configuration")" \
        "$HOSTS_SOURCE/$host_name/host.json"
    if [[ "$agent_name" == "Codex" ]]; then
        new_codex_openai_yaml "$bundle_dir" "$ORCHESTRATION_NAME"
    fi
    local agent_file
    for role in "${ROLE_NAMES[@]}"; do
        if [[ "$agent_name" == "Claude Code" ]]; then agent_file="claude/$role.md"; else agent_file="codex/$role.toml"; fi
        copy_safe_file "$(assert_safe_bundle_path "$agent_root" "$agent_root/agents/$(basename "$agent_file")" "agent definitions")" \
            "$SUBAGENTS_SOURCE/$agent_file"
    done
}

# The dual-review skill's SKILL.md comes from skills/; add its scripts, the Reviewer role,
# and routes.jsonc (only when absent).
install_dual_review_bundle() {
    local agent_name="$1"
    local agent_root="$2"
    local bundle_dir="$agent_root/skills/$DUAL_REVIEW_NAME"
    local host_name routes_source routes_destination script
    host_name="$(host_directory_for "$agent_name")"
    assert_safe_bundle_path "$agent_root" "$bundle_dir" "dual-review bundle" >/dev/null
    for script in "${DUAL_REVIEW_SCRIPTS[@]}"; do
        copy_safe_file "$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/scripts/$script" "dual-review scripts")" \
            "$SUBAGENTS_SOURCE/scripts/$script"
    done
    copy_safe_file "$(assert_safe_bundle_path "$bundle_dir" "$bundle_dir/references/clanker-reviewer.md" "dual-review references")" \
        "$REVIEWER_ROLE_SOURCE"

    routes_source="$HOSTS_SOURCE/$host_name/routes.jsonc"
    routes_destination="$(assert_safe_bundle_path "$agent_root" "$agent_root/clanker/routes.jsonc" "routes file")"
    if [[ -e "$routes_destination" || -L "$routes_destination" ]]; then
        echo "Kept existing routes file: $routes_destination"
    else
        copy_safe_file "$routes_destination" "$routes_source"
    fi

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
    mkdir -p "$agent_skills_root"
    remove_retired_paths "$agent_root"

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

    install_dual_review_bundle "$agent_name" "$agent_root"
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

orchestration_sources=("$HOSTS_SOURCE/claude/host.md" "$HOSTS_SOURCE/claude/host.json" "$HOSTS_SOURCE/codex/host.md" "$HOSTS_SOURCE/codex/host.json")
for role in "${ROLE_NAMES[@]}"; do
    orchestration_sources+=("$SUBAGENTS_SOURCE/$role.md" "$SUBAGENTS_SOURCE/claude/$role.md" "$SUBAGENTS_SOURCE/codex/$role.toml")
done
for orchestration_source in "${orchestration_sources[@]}"; do
    if [[ ! -f "$orchestration_source" ]]; then
        echo "Error: Orchestration role or host source file not found: $orchestration_source" >&2
        exit 1
    fi
done

for dual_review_source in "$SKILLS_SOURCE/$DUAL_REVIEW_NAME.md" "$HOSTS_SOURCE/claude/routes.jsonc" "$HOSTS_SOURCE/codex/routes.jsonc" \
    "${DUAL_REVIEW_SCRIPTS[@]/#/$SUBAGENTS_SOURCE/scripts/}"; do
    if [[ ! -f "$dual_review_source" ]]; then
        echo "Error: Dual-review source file not found: $dual_review_source" >&2
        exit 1
    fi
done

install_agent_links "Claude Code" "$CLAUDE_ROOT" "CLAUDE.md"
install_agent_links "Codex" "$CODEX_ROOT" "AGENTS.md"
install_windsurf_rules "$WINDSURF_MEMORIES_ROOT"
