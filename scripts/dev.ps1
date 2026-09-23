# Локальный запуск (PowerShell): .\scripts\dev.ps1
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
. .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
if (Test-Path .env) { Get-Content .env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim()) } }
uvicorn app.main:app --reload --port 8000
