$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pluginSource = Join-Path $repoRoot "lightroom-plugin\PortraitBatchEdit.lrplugin"
$modules = Join-Path $env:APPDATA "Adobe\Lightroom\Modules"
$pluginTarget = Join-Path $modules "PortraitBatchEdit.lrplugin"
$updated = $false
foreach ($file in Get-ChildItem -LiteralPath $pluginSource -File -Recurse) {
    $relative = $file.FullName.Substring($pluginSource.Length + 1)
    $destination = Join-Path $pluginTarget $relative
    if ((Test-Path -LiteralPath $destination -PathType Leaf) -and
        (Get-FileHash -LiteralPath $file.FullName).Hash -eq (Get-FileHash -LiteralPath $destination).Hash) {
        continue
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    $updated = $true
}
if ($updated) {
    Write-Host "Installed Portrait Batch Edit in $pluginTarget"
    Write-Host "Lightroom Classic loads Modules at startup. If already open, reload the plug-in or restart once."
} else {
    Write-Host "Portrait Batch Edit is up to date in $pluginTarget"
}
