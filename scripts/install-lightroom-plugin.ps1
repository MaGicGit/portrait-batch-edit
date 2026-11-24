$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pluginSource = Join-Path $repoRoot "lightroom-plugin\PortraitBatchEdit.lrplugin"
$modules = Join-Path $env:APPDATA "Adobe\Lightroom\Modules"
$pluginTarget = Join-Path $modules "PortraitBatchEdit.lrplugin"
New-Item -ItemType Directory -Force -Path $modules | Out-Null
New-Item -ItemType Directory -Force -Path $pluginTarget | Out-Null
Copy-Item -Recurse -Force -Path (Join-Path $pluginSource "*") -Destination $pluginTarget
Write-Host "Copied plugin to: $pluginTarget"
Write-Host "Open Lightroom Classic > File > Plug-in Manager and add/enable this plugin."
