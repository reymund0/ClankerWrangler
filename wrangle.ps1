param(
    [string]$ClaudeRoot = (Join-Path $HOME ".claude"),
    [string]$CodexRoot = (Join-Path $HOME ".codex"),
    [string]$WindsurfMemoriesRoot = (Join-Path $HOME ".codeium\windsurf\memories"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$SkillsSource = Join-Path $RepoRoot "skills"
$GlobalRulesSource = Join-Path $RepoRoot "global_rules.md"

function Resolve-ExistingPath {
    param([Parameter(Mandatory)][string]$InputPath)

    if (Test-Path -LiteralPath $InputPath) {
        return (Resolve-Path -LiteralPath $InputPath).ProviderPath
    }

    return $null
}

function Test-SymlinkTarget {
    param(
        [Parameter(Mandatory)][string]$LinkPath,
        [Parameter(Mandatory)][string]$TargetPath
    )

    $item = Get-Item -LiteralPath $LinkPath -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        return $false
    }

    $linkTarget = @($item.Target)[0]
    $resolvedTarget = Resolve-ExistingPath -InputPath $TargetPath
    $resolvedLinkTarget = Resolve-ExistingPath -InputPath $linkTarget

    return $null -ne $resolvedTarget -and $resolvedTarget -eq $resolvedLinkTarget
}

function New-SafeSymlink {
    param(
        [Parameter(Mandatory)][string]$LinkPath,
        [Parameter(Mandatory)][string]$TargetPath
    )

    $existingItem = Get-Item -LiteralPath $LinkPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $existingItem) {
        if (Test-SymlinkTarget -LinkPath $LinkPath -TargetPath $TargetPath) {
            Write-Host "Already linked: $LinkPath"
            return
        }

        if (-not $Force) {
            Write-Warning "Skipping existing path: $LinkPath (pass -Force to replace it)"
            return
        }

        Remove-Item -LiteralPath $LinkPath -Force
    }

    try {
        New-Item -ItemType SymbolicLink -Path $LinkPath -Target $TargetPath | Out-Null
    }
    catch [System.UnauthorizedAccessException] {
        throw "Unable to create symbolic link: $LinkPath. Enable Windows Developer Mode or run this script from an elevated PowerShell session."
    }

    Write-Host "Linked: $LinkPath -> $TargetPath"
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

    $skillFiles = Get-ChildItem -LiteralPath $SkillsSource -Filter "*.md" -File
    foreach ($skillFile in $skillFiles) {
        $skillName = [System.IO.Path]::GetFileNameWithoutExtension($skillFile.Name)
        $skillDirectory = Join-Path $agentSkillsRoot $skillName
        $skillLink = Join-Path $skillDirectory "SKILL.md"

        New-Item -ItemType Directory -Path $skillDirectory -Force | Out-Null
        New-SafeSymlink -LinkPath $skillLink -TargetPath $skillFile.FullName

        if ($AgentName -eq "Codex") {
            New-CodexOpenAIYaml -SkillDirectory $skillDirectory -SkillName $skillName
        }
    }

    New-SafeSymlink -LinkPath $rulesLink -TargetPath $GlobalRulesSource
}

function Install-WindsurfRules {
    param([Parameter(Mandatory)][string]$MemoriesRoot)

    $rulesLink = Join-Path $MemoriesRoot "global_rules.md"

    Write-Host "Configuring Windsurf memories at $MemoriesRoot"

    New-Item -ItemType Directory -Path $MemoriesRoot -Force | Out-Null
    New-SafeSymlink -LinkPath $rulesLink -TargetPath $GlobalRulesSource
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
