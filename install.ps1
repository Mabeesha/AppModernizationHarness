<#
.SYNOPSIS
  Install the Modernization Harness into a working directory.

.DESCRIPTION
  Creates .\out\, drops AGENTS.md and out\INTAKE.md from their templates,
  installs the vendored agent skills (Angular, .NET) into .agents\skills\
  (GitLab Duo Agent Platform layout). Anything it would overwrite is backed up first, under
  .harness-backups\<timestamp>\. It adds nothing to .gitignore.

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

# What older versions appended to the target's .gitignore. Nothing is appended any more:
# GitLab Duo's file tools refuse a git-ignored path, and an agent must be able to read
# everything the harness tells it to read (DD-32). The installer only warns about them.
$OldGitignoreEntries = @('ModernizationHarness/', 'AGENTS.md', '.agents/')

$script:Installed  = 0
$script:BackedUp   = 0
$script:QuietFiles = $false

function Write-Note { param([string] $Message) Write-Host "  $Message" }

function Stop-WithError {
  param([string] $Message)
  Write-Host "error: $Message" -ForegroundColor Red
  exit 1
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

# Never writes; warns about each line an older version appended.
function Test-OldGitignore {
  $gitignore = Join-Path $TargetDir '.gitignore'
  $found = $false
  foreach ($entry in $OldGitignoreEntries) {
    if (Test-GitignoreEntry -Path $gitignore -Entry $entry) {
      Write-Note "warning    .gitignore still ignores $entry - delete that line"
      $found = $true
    }
  }
  if ($found) {
    Write-Note "           (an older install added it; GitLab Duo's file tools cannot read an"
    Write-Note "           ignored path - DEVELOPER_GUIDE.md, Upgrading the Harness Mid-Project)"
  } else {
    Write-Note "nothing to add - the harness files stay readable to the agent's file tools"
  }
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
Test-OldGitignore

Write-Host ''
Write-Host "Done - $script:Installed file(s) written, $script:BackedUp backed up."
if ($script:BackedUp -gt 0) { Write-Host "Backups: $BackupRoot" }
Write-Host ''
Write-Host 'Next: fill in the six blocking questions in out\INTAKE.md (4, 5, 7, 9, 11, 12),'
Write-Host 'then start a session and say "run stage 0".'
