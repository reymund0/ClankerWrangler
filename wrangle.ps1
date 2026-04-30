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
