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
$SubagentsSource = Join-Path $RepoRoot "subagents"
$OrchestrationSkillName = "clanker-orchestration-nation"
$OrchestrationCoordinatorSource = Join-Path $SubagentsSource "$OrchestrationSkillName.md"
$GlobalRulesSource = Join-Path $RepoRoot "global_rules.md"
$CrossReviewLauncherSource = Join-Path $SubagentsSource "scripts\claude_cross_review.py"
$RoutingPolicySource = Join-Path $SubagentsSource "scripts\routing_policy.py"
$RoutingEditorSource = Join-Path $SubagentsSource "scripts\routing_editor.py"
$ModelDiscoverySource = Join-Path $SubagentsSource "scripts\model_discovery.py"
$RoutingDataSource = Join-Path $SubagentsSource "routing"
$RoutingEditorDistSource = Join-Path $RepoRoot "routing-editor\dist"

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

function Assert-PathWithinRoot {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Description
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $rootPrefix = $fullRoot + [System.IO.Path]::DirectorySeparatorChar

    if (-not $fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Description must remain within ${fullRoot}: $fullPath"
    }

    return $fullPath
}

function Assert-NoReparsePath {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Description
    )

    $fullPath = Assert-PathWithinRoot -Path $Path -Root $Root -Description $Description
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $relativePath = $fullPath.Substring($fullRoot.Length).TrimStart([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $currentPath = $fullRoot
    $rootItem = Get-Item -LiteralPath $currentPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $rootItem -and ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to install through a linked $Description root: $currentPath"
    }
    foreach ($part in ($relativePath -split '[\\/]')) {
        if (-not $part) { continue }
        $currentPath = Join-Path $currentPath $part
        $item = Get-Item -LiteralPath $currentPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $item -and ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing to install through a linked $Description path: $currentPath"
        }
    }
    return $fullPath
}

function Remove-RoutingEditorAssets {
    param(
        [Parameter(Mandatory)][string]$EditorDirectory,
        [Parameter(Mandatory)][string]$BundleDirectory
    )

    foreach ($name in @("index.html", "compatibility.json", "assets")) {
        $assetPath = Assert-NoReparsePath -Path (Join-Path $EditorDirectory $name) -Root $BundleDirectory -Description "routing editor"
        $item = Get-Item -LiteralPath $assetPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $item) {
            if ($item.PSIsContainer) {
                foreach ($child in Get-ChildItem -LiteralPath $assetPath -Recurse -Force) {
                    if ($child.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                        throw "Refusing to remove linked editor asset: $($child.FullName)"
                    }
                }
            }
            Remove-Item -LiteralPath $assetPath -Recurse -Force -Confirm:$false
            Write-Host "Removed packaged routing editor asset: $assetPath"
        }
    }
}

function Copy-RoutingDirectory {
    param(
        [Parameter(Mandatory)][string]$SourceDirectory,
        [Parameter(Mandatory)][string]$DestinationDirectory,
        [Parameter(Mandatory)][string]$BundleDirectory,
        [Parameter(Mandatory)][string]$Description
    )

    foreach ($sourceFile in Get-ChildItem -LiteralPath $SourceDirectory -File -Recurse | Where-Object {
        $_.Extension -ne ".pyc" -and $_.FullName -notmatch '[\\/]__pycache__[\\/]'
    } | Sort-Object FullName) {
        $relativePath = $sourceFile.FullName.Substring($SourceDirectory.Length).TrimStart([char[]]@('\', '/'))
        $destinationPath = Assert-NoReparsePath -Path (Join-Path $DestinationDirectory $relativePath) -Root $BundleDirectory -Description $Description
        Copy-SafeFile -DestinationPath $destinationPath -SourcePath $sourceFile.FullName
    }
}

function Install-OrchestrationNationBundle {
    param(
        [Parameter(Mandatory)][string]$AgentName,
        [Parameter(Mandatory)][string]$AgentSkillsRoot,
        [Parameter(Mandatory)][System.IO.FileInfo[]]$SpecialistSourceFiles
    )

    $bundleDirectory = Join-Path $AgentSkillsRoot $OrchestrationSkillName
    $referencesDirectory = Join-Path $bundleDirectory "references"
    $bundleSkill = Join-Path $bundleDirectory "SKILL.md"
    $null = Assert-NoReparsePath -Path $bundleDirectory -Root $AgentSkillsRoot -Description "orchestration bundle"

    New-Item -ItemType Directory -Path $referencesDirectory -Force | Out-Null
    Copy-SafeFile -DestinationPath $bundleSkill -SourcePath $OrchestrationCoordinatorSource

    foreach ($specialistSourceFile in $SpecialistSourceFiles) {
        $referencePath = Join-Path $referencesDirectory $specialistSourceFile.Name
        Copy-SafeFile -DestinationPath $referencePath -SourcePath $specialistSourceFile.FullName
    }

    $scriptsDirectory = Join-Path $bundleDirectory "scripts"
    $scriptsItem = Get-Item -LiteralPath $scriptsDirectory -Force -ErrorAction SilentlyContinue
    if ($null -ne $scriptsItem -and ($scriptsItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to install through a linked scripts directory: $scriptsDirectory"
    }
    Copy-SafeFile -DestinationPath (Join-Path $scriptsDirectory "claude_cross_review.py") -SourcePath $CrossReviewLauncherSource
    foreach ($routingScript in @($RoutingPolicySource, $RoutingEditorSource, $ModelDiscoverySource)) {
        $destination = Assert-NoReparsePath -Path (Join-Path $scriptsDirectory ([System.IO.Path]::GetFileName($routingScript))) -Root $bundleDirectory -Description "routing scripts"
        Copy-SafeFile -DestinationPath $destination -SourcePath $routingScript
    }

    $routingDirectory = Join-Path $bundleDirectory "routing"
    Copy-RoutingDirectory -SourceDirectory $RoutingDataSource -DestinationDirectory $routingDirectory -BundleDirectory $bundleDirectory -Description "routing data"

    $editorDirectory = Join-Path $bundleDirectory "editor"
    Remove-RoutingEditorAssets -EditorDirectory $editorDirectory -BundleDirectory $bundleDirectory
    if (Test-Path -LiteralPath $RoutingEditorDistSource -PathType Container) {
        $compatibilitySource = Join-Path $RoutingEditorDistSource "compatibility.json"
        if (-not (Test-Path -LiteralPath $compatibilitySource -PathType Leaf)) {
            throw "Routing editor build is missing compatibility.json: $RoutingEditorDistSource"
        }
        Copy-RoutingDirectory -SourceDirectory $RoutingEditorDistSource -DestinationDirectory $editorDirectory -BundleDirectory $bundleDirectory -Description "routing editor"
    }
    else {
        Write-Host "Routing editor build unavailable; installed routing helpers without editor assets."
    }

    if ($AgentName -eq "Codex") {
        New-CodexOpenAIYaml -SkillDirectory $bundleDirectory -SkillName $OrchestrationSkillName
    }
}

function Move-OrchestrationSpecialistDirectories {
    param(
        [Parameter(Mandatory)][string]$AgentRoot,
        [Parameter(Mandatory)][string]$AgentSkillsRoot,
        [Parameter(Mandatory)][System.IO.FileInfo[]]$SpecialistSourceFiles
    )

    $backupBase = Join-Path $AgentRoot "backups"
    $backupRoot = Join-Path $backupBase "orchestration-nation"

    foreach ($specialistSourceFile in $SpecialistSourceFiles) {
        $specialistName = [System.IO.Path]::GetFileNameWithoutExtension($specialistSourceFile.Name)
        $sourceDirectory = Join-Path $AgentSkillsRoot $specialistName
        $sourceItem = Get-Item -LiteralPath $sourceDirectory -Force -ErrorAction SilentlyContinue

        if ($null -eq $sourceItem) {
            continue
        }

        if (-not $sourceItem.PSIsContainer -and -not ($sourceItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Cannot migrate non-directory specialist entry: $sourceDirectory"
        }

        foreach ($backupDirectory in @($backupBase, $backupRoot)) {
            $backupItem = Get-Item -LiteralPath $backupDirectory -Force -ErrorAction SilentlyContinue
            if ($null -ne $backupItem -and ($backupItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
                throw "Refusing to migrate through a linked backup directory: $backupDirectory"
            }
        }
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

        $sourceFullPath = Assert-PathWithinRoot -Path $sourceDirectory -Root $AgentSkillsRoot -Description "Specialist source path"
        $destinationBase = Join-Path $backupRoot $specialistName
        $destinationPath = $destinationBase
        $backupIndex = 2

        while ($null -ne (Get-Item -LiteralPath $destinationPath -Force -ErrorAction SilentlyContinue)) {
            $destinationPath = "$destinationBase-$backupIndex"
            $backupIndex++
        }

        $destinationFullPath = Assert-PathWithinRoot -Path $destinationPath -Root $backupRoot -Description "Specialist backup path"
        Move-Item -LiteralPath $sourceFullPath -Destination $destinationFullPath -ErrorAction Stop
        Write-Host "Moved standalone specialist skill to backup: $sourceFullPath -> $destinationFullPath"
    }
}

function Install-AgentLinks {
    param(
        [Parameter(Mandatory)][string]$AgentName,
        [Parameter(Mandatory)][string]$AgentRoot,
        [Parameter(Mandatory)][string]$RulesFileName,
        [Parameter(Mandatory)][System.IO.FileInfo[]]$SpecialistSourceFiles
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

    Install-OrchestrationNationBundle -AgentName $AgentName -AgentSkillsRoot $agentSkillsRoot -SpecialistSourceFiles $SpecialistSourceFiles
    Move-OrchestrationSpecialistDirectories -AgentRoot $AgentRoot -AgentSkillsRoot $agentSkillsRoot -SpecialistSourceFiles $SpecialistSourceFiles

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

if (-not (Test-Path -LiteralPath $SubagentsSource -PathType Container)) {
    throw "Subagents source directory not found: $SubagentsSource"
}

if (-not (Test-Path -LiteralPath $OrchestrationCoordinatorSource -PathType Leaf)) {
    throw "Orchestration coordinator source file not found: $OrchestrationCoordinatorSource"
}

if (-not (Test-Path -LiteralPath $GlobalRulesSource -PathType Leaf)) {
    throw "Global rules file not found: $GlobalRulesSource"
}

if (-not (Test-Path -LiteralPath $CrossReviewLauncherSource -PathType Leaf)) {
    throw "Claude cross-review launcher not found: $CrossReviewLauncherSource"
}

foreach ($routingSource in @($RoutingPolicySource, $RoutingEditorSource, $ModelDiscoverySource)) {
    if (-not (Test-Path -LiteralPath $routingSource -PathType Leaf)) {
        throw "Routing helper source file not found: $routingSource"
    }
}
if (-not (Test-Path -LiteralPath $RoutingDataSource -PathType Container)) {
    throw "Routing data source directory not found: $RoutingDataSource"
}

$SpecialistSourceFiles = @(Get-ChildItem -LiteralPath $SubagentsSource -Filter "*.md" -File | Where-Object { $_.Name -ne "$OrchestrationSkillName.md" } | Sort-Object Name)

Install-AgentLinks -AgentName "Claude Code" -AgentRoot $ClaudeRoot -RulesFileName "CLAUDE.md" -SpecialistSourceFiles $SpecialistSourceFiles
Install-AgentLinks -AgentName "Codex" -AgentRoot $CodexRoot -RulesFileName "AGENTS.md" -SpecialistSourceFiles $SpecialistSourceFiles
Install-WindsurfRules -MemoriesRoot $WindsurfMemoriesRoot
