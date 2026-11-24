$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot ".agents\skills\portrait-batch-edit"
$targetRoot = Join-Path $env:USERPROFILE ".agents\skills"
$target = Join-Path $targetRoot "portrait-batch-edit"

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Recurse -Force -Path (Join-Path $source "*") -Destination $target
Set-Content -LiteralPath (Join-Path $target "project-path.txt") -Value $repoRoot -Encoding UTF8
Write-Host "Installed Codex Skill to: $target"
Write-Host "If Codex does not list it, restart Codex and invoke: `$portrait-batch-edit"
