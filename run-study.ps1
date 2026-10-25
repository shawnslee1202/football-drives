param([string]$PythonExe='python',[switch]$Download)
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    if ($Download) {
        & $PythonExe pipeline.py pull --seasons 2021 2022 2023
        if ($LASTEXITCODE -ne 0) { throw 'Play download failed; completed calls remain cached.' }
        & $PythonExe pipeline.py drives --seasons 2021 2022 2023
        if ($LASTEXITCODE -ne 0) { throw 'Drive download failed; completed calls remain cached.' }
    }
    foreach ($script in @('build_tables.py','study.py','secondary.py','make_deliverables.py','make_tableau.py','validate_release.py')) {
        & $PythonExe $script
        if ($LASTEXITCODE -ne 0) { throw "Failed: $script" }
    }
} finally { Pop-Location }
