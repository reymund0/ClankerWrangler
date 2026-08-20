param(
    [string]$ClaudeRoot = (Join-Path $HOME ".claude"),
    [string]$CodexRoot = (Join-Path $HOME ".codex"),
    [string]$WindsurfMemoriesRoot = (Join-Path $HOME ".codeium\windsurf\memories"),
    [switch]$Force  # retained for call-site compatibility; Copy-SafeFile always overwrites
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$SkillsSource = Join-Path $RepoRoot "skills"
$LegacySkillsSource = Join-Path $SkillsSource "legacy"
$GlobalRulesSource = Join-Path $RepoRoot "global_rules.md"

function Copy-SafeFile {
    param(
        [Parameter(Mandatory)][string]$DestinationPath,
        [Parameter(Mandatory)][string]$SourcePath
    )

    $existingItem = Get-Item -LiteralPath $DestinationPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $existingItem) {
        if ($existingItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            Remove-Item -LiteralPath $DestinationPath -Force
        }
        elseif ($existingItem.PSIsContainer) {
            throw "Cannot replace directory with file: $DestinationPath"
        }
    }

    $destinationDirectory = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null

    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
    Write-Host "Copied: $DestinationPath <- $SourcePath"
}

function ConvertTo-SkillDisplayName {
    param([Parameter(Mandatory)][string]$SkillName)

    $acronyms = @("API", "CI", "CLI", "MCP", "PR", "UI")
    $smallWords = @("and", "or", "to", "up", "with")

    $words = $SkillName -split "-" | Where-Object { $_ }
    $displayWords = for ($i = 0; $i -lt $words.Count; $i++) {
        $word = $words[$i]
        $upperWord = $word.ToUpperInvariant()
        $lowerWord = $word.ToLowerInvariant()

        if ($acronyms -contains $upperWord) {
            $upperWord
        }
        elseif ($i -gt 0 -and $smallWords -contains $lowerWord) {
            $lowerWord
        }
        else {
            $word.Substring(0, 1).ToUpperInvariant() + $word.Substring(1).ToLowerInvariant()
        }
    }

    return ($displayWords -join " ")
}

function ConvertTo-YamlQuotedString {
    param([Parameter(Mandatory)][string]$Value)

    return '"' + ($Value -replace '\\', '\\' -replace '"', '\"' -replace "`n", '\n') + '"'
}

function New-CodexOpenAIYaml {
    param(
        [Parameter(Mandatory)][string]$SkillDirectory,
        [Parameter(Mandatory)][string]$SkillName
    )

    $agentsDirectory = Join-Path $SkillDirectory "agents"
    $openAIYaml = Join-Path $agentsDirectory "openai.yaml"
    $displayName = ConvertTo-SkillDisplayName -SkillName $SkillName
    $shortDescription = "Help with $displayName workflows"
    $defaultPrompt = "Use `$$SkillName to help with this task."

    if ($shortDescription.Length -gt 64) {
        $shortDescription = "$displayName helper"
    }

    New-Item -ItemType Directory -Path $agentsDirectory -Force | Out-Null

    $content = @(
        "interface:"
        "  display_name: $(ConvertTo-YamlQuotedString -Value $displayName)"
        "  short_description: $(ConvertTo-YamlQuotedString -Value $shortDescription)"
        "  default_prompt: $(ConvertTo-YamlQuotedString -Value $defaultPrompt)"
        ""
        "policy:"
        "  allow_implicit_invocation: true"
        ""
    )

    Set-Content -LiteralPath $openAIYaml -Value $content -Encoding utf8
    Write-Host "Generated: $openAIYaml"
}

function Remove-LegacySkills {
    param(
        [Parameter(Mandatory)][string]$AgentSkillsRoot
    )

    if (-not (Test-Path -LiteralPath $LegacySkillsSource -PathType Container)) {
        return
    }

    $legacyFiles = Get-ChildItem -LiteralPath $LegacySkillsSource -Filter "*.md" -File
    foreach ($legacyFile in $legacyFiles) {
        $skillName = [System.IO.Path]::GetFileNameWithoutExtension($legacyFile.Name)
        $skillDirectory = Join-Path $AgentSkillsRoot $skillName

        if (Test-Path -LiteralPath $skillDirectory) {
            Remove-Item -LiteralPath $skillDirectory -Recurse -Force -Confirm:$false
            Write-Host "Removed legacy skill: $skillDirectory"
        }
    }
}

function Install-AgentLinks {
    param(
        [Parameter(Mandatory)][string]$AgentName,
        [Parameter(Mandatory)][string]$AgentRoot,
        [Parameter(Mandatory)][string]$RulesFileName
    )

    $agentSkillsRoot = Join-Path $AgentRoot "skills"
    $rulesLink = Join-Path $AgentRoot $RulesFileName

    Write-Host "Configuring $AgentName at $AgentRoot"

    New-Item -ItemType Directory -Path $AgentRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $agentSkillsRoot -Force | Out-Null

    Remove-LegacySkills -AgentSkillsRoot $agentSkillsRoot

    $skillFiles = Get-ChildItem -LiteralPath $SkillsSource -Filter "*.md" -File
    foreach ($skillFile in $skillFiles) {
        $skillName = [System.IO.Path]::GetFileNameWithoutExtension($skillFile.Name)
        $skillDirectory = Join-Path $agentSkillsRoot $skillName
        $skillLink = Join-Path $skillDirectory "SKILL.md"

        New-Item -ItemType Directory -Path $skillDirectory -Force | Out-Null

        Copy-SafeFile -DestinationPath $skillLink -SourcePath $skillFile.FullName

        if ($AgentName -eq "Codex") {
            New-CodexOpenAIYaml -SkillDirectory $skillDirectory -SkillName $skillName
        }
    }

    Copy-SafeFile -DestinationPath $rulesLink -SourcePath $GlobalRulesSource
}

function Install-WindsurfRules {
    param([Parameter(Mandatory)][string]$MemoriesRoot)

    $rulesLink = Join-Path $MemoriesRoot "global_rules.md"

    Write-Host "Configuring Windsurf memories at $MemoriesRoot"

    New-Item -ItemType Directory -Path $MemoriesRoot -Force | Out-Null
    Copy-SafeFile -DestinationPath $rulesLink -SourcePath $GlobalRulesSource
}

if (-not (Test-Path -LiteralPath $SkillsSource -PathType Container)) {
    throw "Skills source directory not found: $SkillsSource"
}

if (-not (Test-Path -LiteralPath $GlobalRulesSource -PathType Leaf)) {
    throw "Global rules file not found: $GlobalRulesSource"
}

Install-AgentLinks -AgentName "Claude Code" -AgentRoot $ClaudeRoot -RulesFileName "CLAUDE.md"
Install-AgentLinks -AgentName "Codex" -AgentRoot $CodexRoot -RulesFileName "AGENTS.md"
Install-WindsurfRules -MemoriesRoot $WindsurfMemoriesRoot
