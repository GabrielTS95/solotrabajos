$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "No existe .venv. Crea el entorno virtual e instala dependencias antes de ejecutar."
}

if (-not (Test-Path ".\.env.desa")) {
    Write-Error "No existe .env.desa en la carpeta del proyecto."
}

.\.venv\Scripts\python.exe .\ejecutar.py --dataset datasets/test_cases.csv
