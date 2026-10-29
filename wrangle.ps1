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
$HostsSource = Join-Path $SubagentsSource "hosts"
$DualReviewSkillName = "clanker-dual-review"
# The three role references; on Claude each also has an agent definition in subagents\claude\.
$RoleNames = @("clanker-implementor", "clanker-reviewer", "clanker-functional-review")
$DualReviewScripts = @("cross_review.py", "cross_review_codex.py", "clanker_log.py")
$ReviewerRoleSource = Join-Path $SubagentsSource "clanker-reviewer.md"
$RetiredSpecialistNames = @("clanker-ux-designer", "clanker-documentation-writer", "clanker-product-engineer")
# References replaced by another file; only the installed reference is retired, never a standalone skill.
$RetiredReferenceNames = @("clanker-claude-cross-review")

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
        [Parameter(Mandatory)][string]$Description,
        [switch]$AllowLinkedRoot
    )

    $fullPath = Assert-PathWithinRoot -Path $Path -Root $Root -Description $Description
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $relativePath = $fullPath.Substring($fullRoot.Length).TrimStart([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $currentPath = $fullRoot
    $rootItem = Get-Item -LiteralPath $currentPath -Force -ErrorAction SilentlyContinue
    if (-not $AllowLinkedRoot -and $null -ne $rootItem -and ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
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

function Get-RetiredSpecialistEntries {
    param([string]$AgentRoot, [string]$AgentSkillsRoot)

    $references = Join-Path $AgentSkillsRoot "$OrchestrationSkillName\references"
    # The owner-selected agent root may be linked; every descendant must be ordinary.
    $null = Assert-NoReparsePath -Path $references -Root $AgentRoot -Description "specialist references" -AllowLinkedRoot
    $entries = @()
    foreach ($name in $RetiredSpecialistNames) {
        foreach ($extension in @(".md", "")) {
            $source = if ($extension) { Join-Path $references "$name$extension" } else { Join-Path $AgentSkillsRoot $name }
            $source = Assert-NoReparsePath -Path $source -Root $AgentRoot -Description "retired specialist" -AllowLinkedRoot
            $item = Get-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
            if ($null -eq $item) { continue }
            if (($extension -and $item.PSIsContainer) -or (-not $extension -and -not $item.PSIsContainer)) {
                throw "Unexpected retired specialist entry type: $source"
            }
            $entries += [PSCustomObject]@{ Source = $source; Name = $name; Extension = $extension }
        }
    }
    foreach ($name in $RetiredReferenceNames) {
        $source = Assert-NoReparsePath -Path (Join-Path $references "$name.md") -Root $AgentRoot -Description "retired reference" -AllowLinkedRoot
        $item = Get-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
        if ($null -eq $item) { continue }
        if ($item.PSIsContainer) { throw "Unexpected retired reference entry type: $source" }
        $entries += [PSCustomObject]@{ Source = $source; Name = $name; Extension = ".md" }
    }
    if ($entries.Count) {
        foreach ($relative in @("backups", "backups\orchestration-nation")) {
            $backup = Assert-NoReparsePath -Path (Join-Path $AgentRoot $relative) -Root $AgentRoot -Description "retirement backup" -AllowLinkedRoot
            $item = Get-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
            if ($null -ne $item -and -not $item.PSIsContainer) { throw "Backup destination is not a directory: $backup" }
        }
    }
    return $entries
}

function Move-RetiredSpecialistEntries {
    param([string]$AgentRoot, [object[]]$Entries)

    foreach ($entry in $Entries) {
        $source = Assert-NoReparsePath -Path $entry.Source -Root $AgentRoot -Description "retired specialist" -AllowLinkedRoot
        $backupRoot = Assert-NoReparsePath -Path (Join-Path $AgentRoot "backups\orchestration-nation") -Root $AgentRoot -Description "retirement backup" -AllowLinkedRoot
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $destination = Join-Path $backupRoot "$($entry.Name)$($entry.Extension)"
        $suffix = 2
        while ($null -ne (Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue)) {
            $destination = Join-Path $backupRoot "$($entry.Name)-$suffix$($entry.Extension)"
            $suffix++
        }
        $destination = Assert-NoReparsePath -Path $destination -Root $AgentRoot -Description "retirement backup" -AllowLinkedRoot
        Move-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
        Write-Host "Moved retired specialist to backup: $source -> $destination"
    }
}

function Install-OrchestrationNationBundle {
    param(
        [Parameter(Mandatory)][string]$AgentName,
        [Parameter(Mandatory)][string]$AgentRoot,
        [Parameter(Mandatory)][string]$AgentSkillsRoot,
        [Parameter(Mandatory)][System.IO.FileInfo[]]$SpecialistSourceFiles
    )

    $bundleDirectory = Join-Path $AgentSkillsRoot $OrchestrationSkillName
    $referencesDirectory = Join-Path $bundleDirectory "references"
    $bundleSkill = Join-Path $bundleDirectory "SKILL.md"
    $null = Assert-NoReparsePath -Path $bundleDirectory -Root $AgentSkillsRoot -Description "orchestration bundle"
    $retiredEntries = @(Get-RetiredSpecialistEntries -AgentRoot $AgentRoot -AgentSkillsRoot $AgentSkillsRoot)
    $hostName = switch ($AgentName) {
        "Claude Code" { "claude" }
        "Codex" { "codex" }
        default { throw "Unknown orchestration host for ${AgentName}" }
    }

    Copy-SafeFile -DestinationPath $bundleSkill -SourcePath $OrchestrationCoordinatorSource
    foreach ($role in $RoleNames) {
        $referencePath = Assert-NoReparsePath -Path (Join-Path $referencesDirectory "$role.md") -Root $bundleDirectory -Description "role references"
        Copy-SafeFile -DestinationPath $referencePath -SourcePath (Join-Path $SubagentsSource "$role.md")
    }
    $hostReference = Assert-NoReparsePath -Path (Join-Path $referencesDirectory "host.md") -Root $bundleDirectory -Description "host reference"
    Copy-SafeFile -DestinationPath $hostReference -SourcePath (Join-Path $HostsSource "$hostName\host.md")
    $hostConfiguration = Assert-NoReparsePath -Path (Join-Path $bundleDirectory "host.json") -Root $bundleDirectory -Description "host configuration"
    Copy-SafeFile -DestinationPath $hostConfiguration -SourcePath (Join-Path $HostsSource "$hostName\host.json")

    if ($AgentName -eq "Codex") {
        New-CodexOpenAIYaml -SkillDirectory $bundleDirectory -SkillName $OrchestrationSkillName
    }
    Move-RetiredSpecialistEntries -AgentRoot $AgentRoot -Entries $retiredEntries
    if ($AgentName -eq "Claude Code") {
        foreach ($role in $RoleNames) {
            $agentDestination = Assert-NoReparsePath -Path (Join-Path $AgentRoot "agents\$role.md") -Root $AgentRoot -Description "agent definitions"
            Copy-SafeFile -DestinationPath $agentDestination -SourcePath (Join-Path $SubagentsSource "claude\$role.md")
        }
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

# The dual-review skill's SKILL.md comes from skills\; add its scripts, the Reviewer role,
# and routes.jsonc (only when absent).
function Install-DualReviewBundle {
    param(
        [Parameter(Mandatory)][string]$AgentName,
        [Parameter(Mandatory)][string]$AgentRoot,
        [Parameter(Mandatory)][string]$AgentSkillsRoot
    )

    $bundleDirectory = Assert-NoReparsePath -Path (Join-Path $AgentSkillsRoot $DualReviewSkillName) -Root $AgentSkillsRoot -Description "dual-review bundle"
    $hostName = switch ($AgentName) {
        "Claude Code" { "claude" }
        "Codex" { "codex" }
        default { throw "Unknown orchestration host for ${AgentName}" }
    }
    foreach ($script in $DualReviewScripts) {
        $destination = Assert-NoReparsePath -Path (Join-Path $bundleDirectory "scripts\$script") -Root $bundleDirectory -Description "dual-review scripts"
        Copy-SafeFile -DestinationPath $destination -SourcePath (Join-Path $SubagentsSource "scripts\$script")
    }
    $roleDestination = Assert-NoReparsePath -Path (Join-Path $bundleDirectory "references\clanker-reviewer.md") -Root $bundleDirectory -Description "dual-review references"
    Copy-SafeFile -DestinationPath $roleDestination -SourcePath $ReviewerRoleSource

    $routesSource = Join-Path $HostsSource "$hostName\routes.jsonc"
    $routesDestination = Assert-NoReparsePath -Path (Join-Path $AgentRoot "clanker\routes.jsonc") -Root $AgentRoot -Description "routes file"
    if (-not (Test-Path -LiteralPath $routesSource -PathType Leaf)) {
        Write-Host "No routes template for $AgentName yet; skipped $routesDestination"
    } elseif ($null -ne (Get-Item -LiteralPath $routesDestination -Force -ErrorAction SilentlyContinue)) {
        Write-Host "Kept existing routes file: $routesDestination"
    } else {
        Copy-SafeFile -DestinationPath $routesDestination -SourcePath $routesSource
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

    $null = @(Get-RetiredSpecialistEntries -AgentRoot $AgentRoot -AgentSkillsRoot $agentSkillsRoot)

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

    Install-DualReviewBundle -AgentName $AgentName -AgentRoot $AgentRoot -AgentSkillsRoot $agentSkillsRoot
    Install-OrchestrationNationBundle -AgentName $AgentName -AgentRoot $AgentRoot -AgentSkillsRoot $agentSkillsRoot -SpecialistSourceFiles $SpecialistSourceFiles
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

$orchestrationSources = @((Join-Path $HostsSource "claude\host.md"), (Join-Path $HostsSource "claude\host.json"),
    (Join-Path $HostsSource "codex\host.md"), (Join-Path $HostsSource "codex\host.json"))
foreach ($role in $RoleNames) {
    $orchestrationSources += @((Join-Path $SubagentsSource "$role.md"), (Join-Path $SubagentsSource "claude\$role.md"))
}
foreach ($orchestrationSource in $orchestrationSources) {
    if (-not (Test-Path -LiteralPath $orchestrationSource -PathType Leaf)) {
        throw "Orchestration role or host source file not found: $orchestrationSource"
    }
}

$dualReviewSources = @((Join-Path $SkillsSource "$DualReviewSkillName.md"), (Join-Path $HostsSource "claude\routes.jsonc")) +
    @($DualReviewScripts | ForEach-Object { Join-Path $SubagentsSource "scripts\$_" })
foreach ($dualReviewSource in $dualReviewSources) {
    if (-not (Test-Path -LiteralPath $dualReviewSource -PathType Leaf)) {
        throw "Dual-review source file not found: $dualReviewSource"
    }
}

$SpecialistSourceFiles = @(Get-ChildItem -LiteralPath $SubagentsSource -Filter "*.md" -File | Where-Object { $_.Name -ne "$OrchestrationSkillName.md" } | Sort-Object Name)

Install-AgentLinks -AgentName "Claude Code" -AgentRoot $ClaudeRoot -RulesFileName "CLAUDE.md" -SpecialistSourceFiles $SpecialistSourceFiles
Install-AgentLinks -AgentName "Codex" -AgentRoot $CodexRoot -RulesFileName "AGENTS.md" -SpecialistSourceFiles $SpecialistSourceFiles
Install-WindsurfRules -MemoriesRoot $WindsurfMemoriesRoot
