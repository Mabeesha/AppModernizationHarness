<#
.SYNOPSIS
  Install the Modernization Harness into a working directory.

.DESCRIPTION
  Creates .\out\, drops AGENTS.md and out\INTAKE.md from their templates,
  installs the vendored agent skills (Angular, .NET) into .agents\skills\
  (GitLab Duo Agent Platform layout), and adds the harness entries to .gitignore. Anything it
  would overwrite is backed up first, under .harness-backups\<timestamp>\.

.PARAMETER TargetDir
  Where to install. Defaults to the current directory.

.PARAMETER Update
  Before installing, run .\update-skills.ps1 to re-vendor the official Angular
  and .NET skills into ModernizationHarness\skills\. Rewrites files in this repo,
  so the change shows up in git. Skills you write yourself are left alone.

.PARAMETER DryRun
  Print what would happen; change nothing.

.EXAMPLE
  .\install.ps1

.EXAMPLE
  .\install.ps1 -TargetDir D:\work\my-app -Update
#>
[CmdletBinding()]
param(
  [string] $TargetDir = (Get-Location).Path,
  [switch] $Update,
  [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$HarnessDir    = Join-Path $ScriptDir 'ModernizationHarness'
$SkillsDir     = Join-Path $HarnessDir 'skills'
$Stamp         = Get-Date -Format 'yyyyMMdd-HHmmss'

# Appended to the target's .gitignore if not already covered.
$GitignoreHeader  = '# Modernization Harness'
$GitignoreEntries = @('ModernizationHarness/', 'AGENTS.md', '.agents/')

$script:Installed  = 0
$script:BackedUp   = 0
$script:QuietFiles = $false

function Write-Note { param([string] $Message) Write-Host "  $Message" }

function Stop-WithError {
  param([string] $Message)
  Write-Host "error: $Message" -ForegroundColor Red
  exit 1
}

# Write UTF-8 with no BOM; Set-Content in Windows PowerShell 5.1 would add one.
function Write-TextFile {
  param([string] $Path, [string] $Text)
  $dir = Split-Path -Parent $Path
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

if (-not (Test-Path -LiteralPath $HarnessDir)) {
  Stop-WithError "no ModernizationHarness\ next to this script ($HarnessDir)"
}

# --- refresh the vendored skills (update-skills.ps1 does the downloading) ---

if ($Update) {
  $updateArgs = @{}
  if ($DryRun) { $updateArgs.DryRun = $true }
  & (Join-Path $ScriptDir 'update-skills.ps1') @updateArgs
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host ''
}

# --- install ---------------------------------------------------------------

if (-not (Test-Path -LiteralPath $TargetDir)) {
  if ($DryRun) {
    Write-Note "(dry run) mkdir $TargetDir"
  } else {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
  }
}
if (Test-Path -LiteralPath $TargetDir) { $TargetDir = (Resolve-Path -LiteralPath $TargetDir).Path }
$BackupRoot = Join-Path $TargetDir ".harness-backups\$Stamp"

function Install-HarnessFile {
  param([string] $Source, [string] $Destination)

  if (-not (Test-Path -LiteralPath $Source)) { Stop-WithError "template missing: $Source" }
  $rel = $Destination.Substring($TargetDir.Length).TrimStart('\', '/')

  if (Test-Path -LiteralPath $Destination) {
    $srcHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
    $dstHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
    if ($srcHash -eq $dstHash) {
      if (-not $script:QuietFiles) { Write-Note "unchanged  $rel" }
      return
    }

    if ($DryRun) {
      Write-Note "(dry run) $rel -> backup, then overwrite"
    } else {
      $backup = Join-Path $BackupRoot $rel
      $backupDir = Split-Path -Parent $backup
      if (-not (Test-Path -LiteralPath $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
      }
      Move-Item -LiteralPath $Destination -Destination $backup -Force
      Write-Note "backed up  $rel -> .harness-backups\$Stamp\$rel"
      $script:BackedUp++
    }
  }

  if ($DryRun) {
    if (-not $script:QuietFiles) { Write-Note "(dry run) write $rel" }
  } else {
    $destDir = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $destDir)) {
      New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    if (-not $script:QuietFiles) { Write-Note "installed  $rel" }
  }
  $script:Installed++
}

# True if a non-comment line already names the entry, with or without a
# trailing slash.
function Test-GitignoreEntry {
  param([string] $Path, [string] $Entry)
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $wanted = $Entry.TrimEnd('/')
  foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
    $trimmed = $line.Trim()
    if ($trimmed.Length -eq 0) { continue }
    if ($trimmed.StartsWith('#')) { continue }
    if ($trimmed.TrimEnd('/') -eq $wanted) { return $true }
  }
  return $false
}

function Update-Gitignore {
  $gitignore = Join-Path $TargetDir '.gitignore'
  $missing = @()

  foreach ($entry in $GitignoreEntries) {
    if (Test-GitignoreEntry -Path $gitignore -Entry $entry) {
      Write-Note "present    $entry"
    } else {
      $missing += $entry
    }
  }

  if ($missing.Count -eq 0) { return }

  if ($DryRun) {
    foreach ($entry in $missing) { Write-Note "(dry run) append $entry" }
    return
  }

  $nl = [char]10
  $existing = ''
  if (Test-Path -LiteralPath $gitignore) {
    # Match whatever line ending the file already uses.
    if ([System.IO.File]::ReadAllText($gitignore) -match ([char]13 + [char]10)) {
      $nl = [string]([char]13) + [char]10
    }
    $backup = Join-Path $BackupRoot '.gitignore'
    $backupDir = Split-Path -Parent $backup
    if (-not (Test-Path -LiteralPath $backupDir)) {
      New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $gitignore -Destination $backup -Force
    Write-Note "backed up  .gitignore -> .harness-backups\$Stamp\.gitignore"
    $script:BackedUp++

    # Keep the file's existing line endings; separate from what came before
    # without stacking blank lines.
    $existing = [System.IO.File]::ReadAllText($gitignore)
    $existing = $existing.TrimEnd([char]10, [char]13) + $nl + $nl
  } else {
    Write-Note "created    .gitignore"
  }

  $text = $existing + $GitignoreHeader + $nl
  foreach ($entry in $missing) { $text += $entry + $nl }
  Write-TextFile $gitignore $text

  foreach ($entry in $missing) { Write-Note "appended   $entry" }
  $script:Installed++
}

Write-Host "Installing the Modernization Harness into $TargetDir"
Write-Host ''

Write-Host 'Artifact directory'
$outDir = Join-Path $TargetDir 'out'
if (-not (Test-Path -LiteralPath $outDir)) {
  if ($DryRun) { Write-Note "(dry run) mkdir $outDir" }
  else { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
}
Write-Note 'out\'

Write-Host ''
Write-Host 'Project files'
Install-HarnessFile (Join-Path $HarnessDir 'AGENTS_TEMPLATE.md')   (Join-Path $TargetDir 'AGENTS.md')
Install-HarnessFile (Join-Path $HarnessDir '0_INTAKE_TEMPLATE.md') (Join-Path $TargetDir 'out\INTAKE.md')

Write-Host ''
Write-Host 'Agent skills (.agents\skills - GitLab Duo layout)'
$found = $false
if (Test-Path -LiteralPath $SkillsDir) {
  foreach ($skillDir in (Get-ChildItem -LiteralPath $SkillsDir -Directory | Sort-Object Name)) {
    if (-not (Test-Path -LiteralPath (Join-Path $skillDir.FullName 'SKILL.md'))) {
      Write-Note "skipped    $($skillDir.Name) (no SKILL.md)"
      continue
    }
    $found = $true
    $files = @(Get-ChildItem -LiteralPath $skillDir.FullName -File -Recurse | Sort-Object FullName)
    $before = $script:Installed
    $script:QuietFiles = $true
    foreach ($file in $files) {
      $rel  = $file.FullName.Substring($skillDir.FullName.Length).TrimStart('\', '/')
      $dest = Join-Path $TargetDir ".agents\skills\$($skillDir.Name)\$rel"
      Install-HarnessFile $file.FullName $dest
    }
    $script:QuietFiles = $false
    $written = $script:Installed - $before
    if ($written -eq 0) {
      Write-Note "unchanged  .agents\skills\$($skillDir.Name)\ ($($files.Count) file(s))"
    } else {
      Write-Note "installed  .agents\skills\$($skillDir.Name)\ ($($files.Count) file(s), $written written)"
    }
  }
}
if (-not $found) { Write-Note 'none vendored - run: .\update-skills.ps1' }

Write-Host ''
Write-Host '.gitignore'
Update-Gitignore

Write-Host ''
Write-Host "Done - $script:Installed file(s) written, $script:BackedUp backed up."
if ($script:BackedUp -gt 0) { Write-Host "Backups: $BackupRoot" }
Write-Host ''
Write-Host 'Next: fill in the six blocking questions in out\INTAKE.md (4, 5, 7, 9, 11, 12),'
Write-Host 'then start a session and say "run stage 0".'
