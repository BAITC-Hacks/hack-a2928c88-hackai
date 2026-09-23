# Почасовой чекпоинт (п. 6.6): .\scripts\checkpoint.ps1 -Hour 2 -Note "основной сценарий работает end-to-end"
param([Parameter(Mandatory)][int]$Hour, [Parameter(Mandatory)][string]$Note)
$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "HH:mm"
Add-Content -Encoding utf8 docs/PROGRESS.md "`n## Час $Hour — $ts`n- $Note`n- Коммит: (см. git log, тег hour-$Hour)"
python -m pytest -q; if ($LASTEXITCODE -ne 0) { Write-Warning "Тесты падают — чекпоинт всё равно фиксируется, починить в следующем часу" }
git add -A
git commit -m "checkpoint(hour-$Hour): $Note"
git tag -f "hour-$Hour"
git push; git push -f origin "hour-$Hour"
Write-Host "Чекпоинт часа $Hour отправлен."
