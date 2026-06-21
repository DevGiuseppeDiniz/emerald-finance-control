$ErrorActionPreference = "Stop"

function Test-PythonTk {
    param([string]$Command)
    try {
        & $Command -c "import tkinter; print('ok')" | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        py -3 -c "import tkinter; print('ok')" | Out-Null
        py -3 .\main.py
        exit $LASTEXITCODE
    } catch {
    }
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    if (Test-PythonTk "python") {
        python .\main.py
        exit $LASTEXITCODE
    }
}

Write-Host "Nao encontrei um Python com Tkinter disponivel no PATH."
Write-Host "Instale Python 3.11+ pelo python.org marcando a opcao Tcl/Tk, depois execute:"
Write-Host "  .\run.ps1"
exit 1
