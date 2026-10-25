param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$priorKey = $env:CFBD_API_KEY
$keyPointer = [IntPtr]::Zero
try {
    if (-not $env:CFBD_API_KEY -and -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.env'))) {
        $maskedKey = Read-Host 'CollegeFootballData API key (hidden; used for this run only)' -AsSecureString
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($maskedKey)
        $env:CFBD_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    }
    & $PythonExe (Join-Path $PSScriptRoot 'pipeline.py') pull --seasons 2022 2023
    if ($LASTEXITCODE -ne 0) { throw 'Download or export failed; completed requests remain cached.' }
    & $PythonExe (Join-Path $PSScriptRoot 'pipeline.py') analyze --team 'Texas A&M' --baseline-season 2022 --season 2023 --change-date 2023-11-12
    if ($LASTEXITCODE -ne 0) { throw 'Exploratory analysis failed; inspect the data and baseline coverage.' }
} finally {
    $env:CFBD_API_KEY = $priorKey
    if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    if ($maskedKey) { $maskedKey.Dispose() }
}
