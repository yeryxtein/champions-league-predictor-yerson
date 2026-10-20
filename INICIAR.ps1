$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$sharedPython = Join-Path $PSScriptRoot '../../work/champions_env/Scripts/python.exe'
$localPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $sharedPython) {
    $projectPython = (Resolve-Path -LiteralPath $sharedPython).Path
} elseif (Test-Path -LiteralPath $localPython) {
    $projectPython = $localPython
} else {
    $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $bundledPython) {
        $basePython = $bundledPython
    } elseif ($pythonCommand) {
        $basePython = $pythonCommand.Source
    } else {
        throw 'Instala Python 3.12 o superior y vuelve a ejecutar INICIAR.cmd.'
    }
    & $basePython -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python.' }
    $projectPython = $localPython
}
& $projectPython -c 'import fastapi, uvicorn, streamlit, pandas, requests'
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Instalando dependencias. La primera vez requiere internet...'
    & $projectPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-lock.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
}
& $projectPython (Join-Path $PSScriptRoot 'iniciar.py')
