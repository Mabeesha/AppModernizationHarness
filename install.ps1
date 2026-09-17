<#
.SYNOPSIS
  Install the Modernization Harness into a working directory.

.DESCRIPTION
  Creates .\out\, drops AGENTS.md and out\INTAKE.md from their templates, and
  installs the bundled agent skills into .agents\skills\ (GitLab Duo Agent
  Platform layout). Anything it would overwrite is backed up first, under
  .harness-backups\<timestamp>\.

.PARAMETER TargetDir
  Where to install. Defaults to the current directory.

.PARAMETER Update
  Before installing, re-vendor the official Angular skills from
  github.com/angular/skills into ModernizationHarness\skills\. Rewrites files in
  this repo, so the change shows up in git. Only directories listed in
  skills\.upstream-angular are replaced; skills you write yourself are left alone.

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
$Manifest      = Join-Path $SkillsDir '.upstream-angular'
$AngularRepo   = 'https://github.com/angular/skills'
$AngularZipUrl = 'https://codeload.github.com/angular/skills/zip/refs/heads/main'
$Stamp         = Get-Date -Format 'yyyyMMdd-HHmmss'

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

# --- re-vendor the official Angular skills ---------------------------------

function Get-VendoredSkillName {
  if (-not (Test-Path -LiteralPath $Manifest)) { return @() }
  $names = @()
  foreach ($line in [System.IO.File]::ReadAllLines($Manifest)) {
    if ($line -like 'skill=*') { $names += $line.Substring(6).Trim() }
  }
  return $names
}

function Update-AngularSkill {
  Write-Host "Re-vendoring the official Angular skills from $AngularRepo"
  if ($DryRun) { Write-Note "(dry run) would rewrite $SkillsDir"; return }

  $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('angular-skills-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  try {
    $zip = Join-Path $tmp 'skills.zip'
    try {
      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      Invoke-WebRequest -Uri $AngularZipUrl -OutFile $zip -UseBasicParsing
    } catch {
      Stop-WithError "download failed ($($_.Exception.Message)) - leaving the vendored copies alone"
    }
    if (-not (Test-Path -LiteralPath $zip) -or (Get-Item -LiteralPath $zip).Length -eq 0) {
      Stop-WithError 'downloaded an empty archive - leaving the vendored copies alone'
    }

    $extract = Join-Path $tmp 'x'
    try {
      Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
    } catch {
      Stop-WithError "could not extract the archive ($($_.Exception.Message))"
    }

    $root = Get-ChildItem -LiteralPath $extract -Directory | Where-Object { $_.Name -like 'skills-*' } | Select-Object -First 1
    if ($null -eq $root) { Stop-WithError 'unexpected archive layout - no skills-* directory' }

    # Drop only what we vendored last time; hand-written skills stay.
    foreach ($old in Get-VendoredSkillName) {
      if ([string]::IsNullOrWhiteSpace($old)) { continue }
      $oldPath = Join-Path $SkillsDir $old
      if (Test-Path -LiteralPath $oldPath) {
        Remove-Item -LiteralPath $oldPath -Recurse -Force
        Write-Note "removed    skills\$old (will be replaced)"
      }
    }

    if (-not (Test-Path -LiteralPath $SkillsDir)) {
      New-Item -ItemType Directory -Path $SkillsDir -Force | Out-Null
    }

    $names = @()
    foreach ($dir in (Get-ChildItem -LiteralPath $root.FullName -Directory | Sort-Object Name)) {
      if (-not (Test-Path -LiteralPath (Join-Path $dir.FullName 'SKILL.md'))) { continue }
      $dest = Join-Path $SkillsDir $dir.Name
      Copy-Item -LiteralPath $dir.FullName -Destination $dest -Recurse -Force
      $count = @(Get-ChildItem -LiteralPath $dest -File -Recurse).Count
      Write-Note "vendored   skills\$($dir.Name) ($count file(s))"
      $names += $dir.Name
    }
    if ($names.Count -eq 0) { Stop-WithError 'the archive contained no SKILL.md directories' }

    $commit = 'unknown'
    $built  = 'unknown'
    $buildInfo = Join-Path $root.FullName 'BUILD_INFO'
    if (Test-Path -LiteralPath $buildInfo) {
      $lines = @([System.IO.File]::ReadAllLines($buildInfo))
      if ($lines.Count -ge 1) { $built  = $lines[0] }
      if ($lines.Count -ge 2) { $commit = $lines[1] }
    }

    $nl    = [char]10
    $text  = "# Directories in this folder vendored from $AngularRepo" + $nl
    $text += '# Refresh with ./install.sh --update (or .\install.ps1 -Update). Do not hand-edit.' + $nl
    $text += "source=$AngularRepo" + $nl
    $text += 'ref=main' + $nl
    $text += "commit=$commit" + $nl
    $text += "built=$built" + $nl
    foreach ($name in $names) { $text += "skill=$name" + $nl }
    Write-TextFile $Manifest $text

    $short = $commit
    if ($short.Length -gt 12) { $short = $short.Substring(0, 12) }
    Write-Note "manifest   skills\.upstream-angular (upstream commit $short)"
  } finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
  }
}

if ($Update) { Update-AngularSkill }

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
if (-not $found) { Write-Note 'none vendored - run: .\install.ps1 -Update' }

Write-Host ''
Write-Host "Done - $script:Installed file(s) written, $script:BackedUp backed up."
if ($script:BackedUp -gt 0) { Write-Host "Backups: $BackupRoot" }
Write-Host ''
Write-Host 'Next: fill in the six blocking questions in out\INTAKE.md (4, 5, 7, 9, 11, 12),'
Write-Host 'then start a session and say "run stage 0".'
