<#
.SYNOPSIS
  Refresh the agent skills vendored into ModernizationHarness\skills\.

.DESCRIPTION
  Downloads each trusted upstream at one exact commit and rewrites only the
  skill directories that upstream owns (listed in skills\.upstream-<source>).
  Skills you write yourself are never touched. The result is an ordinary,
  reviewable git diff in this repo.

  The trusted upstreams are fixed on purpose; there is no option to download
  from anywhere else:
    angular  github.com/angular/skills  skills sit at the repo root
    dotnet   github.com/dotnet/skills   skills sit under plugins\<plugin>\skills\

.PARAMETER Source
  angular, dotnet, or all (default: all).

.PARAMETER DryRun
  Download and report what would change; write nothing.

.EXAMPLE
  .\update-skills.ps1

.EXAMPLE
  .\update-skills.ps1 -Source dotnet -DryRun
#>
[CmdletBinding()]
param(
  [ValidateSet('angular', 'dotnet', 'all')]
  [string] $Source = 'all',
  [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir = Join-Path $ScriptDir 'ModernizationHarness\skills'

$Repos = [ordered]@{ angular = 'angular/skills'; dotnet = 'dotnet/skills' }

# Which dotnet/skills plugins to take. Keep in step with update-skills.sh.
$DotnetPlugins = @('dotnet', 'dotnet-aspnetcore', 'dotnet-data', 'dotnet-test')

function Write-Note { param([string] $Message) Write-Host "  $Message" }

function Stop-WithError {
  param([string] $Message)
  Write-Host "error: $Message" -ForegroundColor Red
  exit 1
}

# Write UTF-8 with no BOM and LF endings, matching update-skills.sh.
function Write-TextFile {
  param([string] $Path, [string] $Text)
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

# Skill names become directory names, here and in the target; keep them plain.
function Assert-SkillName {
  param([string] $Name)
  if ($Name -notmatch '^[A-Za-z0-9_-][A-Za-z0-9._-]*$') { Stop-WithError "refusing unsafe skill name '$Name'" }
}

# The directories a source vendored last time.
function Get-OwnedSkill {
  param([string] $Name)
  $manifest = Join-Path $SkillsDir ".upstream-$Name"
  $owned = @()
  if (-not (Test-Path -LiteralPath $manifest)) { return $owned }
  foreach ($line in [System.IO.File]::ReadAllLines($manifest)) {
    if ($line -like 'skill=*') {
      $skill = $line.Substring(6).Trim()
      Assert-SkillName $skill
      $owned += $skill
    }
  }
  return $owned
}

# HTTPS only, and no redirects: a redirect could only lead somewhere we did not name.
function Invoke-Download {
  param([string] $Uri, [hashtable] $Headers = @{}, [string] $OutFile)
  $params = @{ Uri = $Uri; Headers = $Headers; UseBasicParsing = $true; MaximumRedirection = 0 }
  if ($OutFile) { $params.OutFile = $OutFile; $params.PassThru = $true }
  $response = Invoke-WebRequest @params
  if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode) from $Uri" }
  return $response
}

if ($Source -eq 'all') { $Selected = @($Repos.Keys) } else { $Selected = @($Source) }

if (-not (Test-Path -LiteralPath $SkillsDir)) {
  Stop-WithError "no ModernizationHarness\skills\ next to this script ($SkillsDir)"
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('harness-skills-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $Tmp -Force | Out-Null

try {
  Write-Host "Updating vendored skills in $SkillsDir"

  # --- 1. download and check every source before touching anything ----------

  $plans  = @()
  $allNew = @()

  foreach ($name in $Selected) {
    $repo = $Repos[$name]

    try {
      $r = Invoke-Download -Uri "https://api.github.com/repos/$repo/commits/main" -Headers @{ Accept = 'application/vnd.github.sha' }
      $sha = $r.Content
      if ($sha -is [byte[]]) { $sha = [System.Text.Encoding]::UTF8.GetString($sha) }
      $sha = "$sha".Trim()
    } catch {
      Stop-WithError "could not ask GitHub which commit $repo is at ($($_.Exception.Message)) - nothing was changed"
    }
    if ($sha -notmatch '^[0-9a-f]{40}$') { Stop-WithError "GitHub did not return a commit id for $repo - nothing was changed" }

    $dir = Join-Path $Tmp $name
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $zip = Join-Path $dir 'src.zip'
    try {
      Invoke-Download -Uri "https://codeload.github.com/$repo/zip/$sha" -OutFile $zip | Out-Null
    } catch {
      Stop-WithError "download of $repo failed ($($_.Exception.Message)) - nothing was changed"
    }
    if (-not (Test-Path -LiteralPath $zip) -or (Get-Item -LiteralPath $zip).Length -eq 0) {
      Stop-WithError "downloaded an empty $repo archive - nothing was changed"
    }
    # Unpack only what gets vendored (top-level files, plus the chosen plugins'
    # skills for dotnet). Not Expand-Archive: in Windows PowerShell 5.1 it fails on
    # dot-folders, and dotnet/skills has test paths past the 260-character limit.
    $top = "$($repo.Split('/')[1])-$sha/"
    if ($name -eq 'dotnet') { $keep = @($DotnetPlugins | ForEach-Object { "plugins/$_/skills/" }) } else { $keep = @('') }
    $dirFull = [System.IO.Path]::GetFullPath($dir) + [System.IO.Path]::DirectorySeparatorChar
    try {
      Add-Type -AssemblyName System.IO.Compression.FileSystem
      $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
      try {
        foreach ($entry in $archive.Entries) {
          if (-not $entry.FullName.StartsWith($top)) { throw "entry outside $top`: $($entry.FullName)" }
          $rel = $entry.FullName.Substring($top.Length)
          if ($rel -eq '' -or $rel.EndsWith('/')) { continue }
          $wanted = -not $rel.Contains('/')
          foreach ($k in $keep) { if ($rel.StartsWith($k)) { $wanted = $true; break } }
          if (-not $wanted) { continue }
          $dest = [System.IO.Path]::GetFullPath((Join-Path $dir $entry.FullName))
          if (-not $dest.StartsWith($dirFull)) { throw "entry escapes the archive folder: $($entry.FullName)" }
          New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
          [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $dest, $true)
        }
      } finally {
        $archive.Dispose()
      }
    } catch {
      Stop-WithError "could not extract the $repo archive ($($_.Exception.Message)) - nothing was changed"
    }
    $root = Join-Path $dir ("$($repo.Split('/')[1])-$sha")
    if (-not (Test-Path -LiteralPath $root)) { Stop-WithError "unexpected $repo archive layout - no $($repo.Split('/')[1])-$sha directory" }

    if ($name -eq 'dotnet') {
      $parents = @()
      foreach ($plugin in $DotnetPlugins) {
        $p = Join-Path $root "plugins\$plugin\skills"
        if (-not (Test-Path -LiteralPath $p)) { Stop-WithError "dotnet/skills has no plugin '$plugin' - fix `$DotnetPlugins; nothing was changed" }
        $parents += $p
      }
    } else {
      $parents = @($root)
    }

    $old = @(Get-OwnedSkill $name)
    $skills = @()
    foreach ($parent in $parents) {
      # Ordinal order, so the manifest comes out the same as from update-skills.sh.
      $dirs = @(Get-ChildItem -LiteralPath $parent -Directory)
      [Array]::Sort([string[]]@($dirs | ForEach-Object { $_.Name }), [object[]]$dirs, [StringComparer]::Ordinal)
      foreach ($d in $dirs) {
        if (-not (Test-Path -LiteralPath (Join-Path $d.FullName 'SKILL.md'))) { continue }
        Assert-SkillName $d.Name
        if ($allNew -contains $d.Name) { Stop-WithError "two upstream skills are both called '$($d.Name)' - nothing was changed" }
        if ((Test-Path -LiteralPath (Join-Path $SkillsDir $d.Name)) -and -not ($old -contains $d.Name)) {
          Stop-WithError "skills\$($d.Name) already exists and did not come from $repo - rename one of them; nothing was changed"
        }
        $allNew += $d.Name
        $skills += [pscustomobject]@{ Name = $d.Name; Path = $d.FullName }
      }
    }
    if ($skills.Count -eq 0) { Stop-WithError "$repo has no SKILL.md directories where expected - nothing was changed" }

    $plans += [pscustomobject]@{ Source = $name; Repo = $repo; Sha = $sha; Root = $root; Old = $old; Skills = $skills }
  }

  # --- 2. apply ---------------------------------------------------------------

  foreach ($plan in $plans) {
    Write-Host ''
    Write-Host "$($plan.Source) - github.com/$($plan.Repo) @ $($plan.Sha.Substring(0, 12))"
    $newNames = @($plan.Skills | ForEach-Object { $_.Name })

    foreach ($old in $plan.Old) {
      if (-not ($newNames -contains $old)) { Write-Note "removed    skills\$old (no longer upstream)" }
    }

    if ($DryRun) {
      foreach ($n in $newNames) {
        if ($plan.Old -contains $n) { Write-Note "(dry run) replace skills\$n" }
        else { Write-Note "(dry run) add     skills\$n" }
      }
      continue
    }

    foreach ($old in $plan.Old) {
      $oldPath = Join-Path $SkillsDir $old
      if (Test-Path -LiteralPath $oldPath) { Remove-Item -LiteralPath $oldPath -Recurse -Force }
    }

    foreach ($skill in $plan.Skills) {
      $dest = Join-Path $SkillsDir $skill.Name
      Copy-Item -LiteralPath $skill.Path -Destination $dest -Recurse -Force
      $count = @(Get-ChildItem -LiteralPath $dest -File -Recurse -Force).Count
      Write-Note "vendored   skills\$($skill.Name) ($count file(s))"
    }

    # Both upstreams are MIT, which asks that the licence travel with the copy.
    foreach ($f in @('LICENSE', 'LICENSE.md', 'LICENSE.txt')) {
      $lic = Join-Path $plan.Root $f
      if (Test-Path -LiteralPath $lic) {
        Copy-Item -LiteralPath $lic -Destination (Join-Path $SkillsDir "LICENSE-$($plan.Source)") -Force
        break
      }
    }

    $nl    = [char]10
    $text  = "# Skill directories in this folder vendored from https://github.com/$($plan.Repo)" + $nl
    $text += '# Refresh with ./update-skills.sh (or .\update-skills.ps1). Do not hand-edit.' + $nl
    $text += "source=https://github.com/$($plan.Repo)" + $nl
    $text += 'ref=main' + $nl
    $text += "commit=$($plan.Sha)" + $nl
    $buildInfo = Join-Path $plan.Root 'BUILD_INFO'
    if (Test-Path -LiteralPath $buildInfo) {
      $lines = @([System.IO.File]::ReadAllLines($buildInfo))
      if ($lines.Count -ge 1) { $text += "built=$($lines[0])" + $nl }
    }
    if ($plan.Source -eq 'dotnet') {
      foreach ($plugin in $DotnetPlugins) { $text += "plugin=$plugin" + $nl }
    }
    foreach ($n in $newNames) { $text += "skill=$n" + $nl }
    Write-TextFile (Join-Path $SkillsDir ".upstream-$($plan.Source)") $text
    Write-Note "manifest   skills\.upstream-$($plan.Source)"
  }

  Write-Host ''
  if ($DryRun) { Write-Host 'Dry run - nothing was written.' }
  else { Write-Host 'Done. Review with: git diff --stat -- ModernizationHarness/skills' }
} finally {
  if (Test-Path -LiteralPath $Tmp) { Remove-Item -LiteralPath $Tmp -Recurse -Force }
}
