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

install_agent_links "Claude Code" "$CLAUDE_ROOT" "CLAUDE.md"
install_agent_links "Codex" "$CODEX_ROOT" "AGENTS.md"
install_windsurf_rules "$WINDSURF_MEMORIES_ROOT"
