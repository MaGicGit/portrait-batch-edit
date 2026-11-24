$ErrorActionPreference = "Stop"
$pythonBin = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Push-Location (Join-Path $PSScriptRoot "python")
try {
    if (Test-Path -LiteralPath $pythonBin) {
        & $pythonBin -m unittest discover -s tests -v
    } else {
        py -3 -m unittest discover -s tests -v
    }
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
