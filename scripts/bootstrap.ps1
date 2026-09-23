# Развернуть каркас в репозиторий, выданный платформой.
#   .\scripts\bootstrap.ps1 -Target C:\path\to\platform-repo -Track 5
param([Parameter(Mandatory)][string]$Target, [Parameter(Mandatory)][ValidateRange(1,10)][int]$Track)
$ErrorActionPreference = "Stop"
$Src = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Target ".git"))) { throw "$Target — не git-репозиторий. Сначала git clone репозитория платформы." }
$exclude = @(".venv", "venv", "logs", "__pycache__", ".pytest_cache", ".git", ".env", "wheels")
Get-ChildItem -Force $Src | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
  Copy-Item -Recurse -Force $_.FullName (Join-Path $Target $_.Name)
}
$nn = "{0:D2}" -f $Track
Copy-Item -Force (Join-Path $Src "context\ideas\track-$nn.md") (Join-Path $Target "docs\IDEA.md")
Copy-Item -Force (Join-Path $Src "context\tracks\track-$nn.md") (Join-Path $Target "docs\TRACK.md")
$samples = Join-Path $Src "context\samples\track-$nn"
if (Test-Path $samples) {
  Get-ChildItem -File $samples | Copy-Item -Destination (Join-Path $Target "data\samples") -Force
  if (Test-Path "$samples\eval") { Get-ChildItem -File "$samples\eval" | Copy-Item -Destination (Join-Path $Target "eval\cases") -Force }
}
if (-not (Test-Path (Join-Path $Target "docs\CASE.md"))) {
  Set-Content -Encoding utf8 (Join-Path $Target "docs\CASE.md") "# Кейс организаторов (вставить дословно)`n"
}
Push-Location $Target
git add -A
git commit -m "chore: import pre-built harness (disclosed in docs/DISCLOSURE.md), track $Track"
Pop-Location
Write-Host "Готово. Дальше: вставить кейс в docs/CASE.md, затем /kickoff $Track (Claude) или codex 'Выполни prompts/00-kickoff.md'."
