# Проверка ноутбука перед хакатоном: .\scripts\preflight.ps1   (добавить -Wheels, чтобы скачать пакеты офлайн)
param([switch]$Wheels)
$ok = 0; $bad = 0
function Check($name, $cond, $hint) {
  if ($cond) { Write-Host "[OK]  $name" -ForegroundColor Green; $script:ok++ }
  else { Write-Host "[!!]  $name — $hint" -ForegroundColor Red; $script:bad++ }
}
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

$radio = (netsh wlan show drivers) -join "`n"
Check "Wi-Fi 5 ГГц (802.11a/ac/ax)" ($radio -match "802\.11(a|ac|ax)\b") "по регламенту без 5 ГГц не допустят; взять USB-адаптер 5 ГГц"
Check "python" (Has python) "поставить Python 3.12 (python.org), галочка Add to PATH"
if (Has python) { $v = python --version; Check "Python >= 3.11 ($v)" ($v -match "3\.(1[1-9])") "нужен 3.11+" }
Check "git" (Has git) "поставить Git for Windows"
if (Has git) { Check "git user.name" ([bool](git config --global user.name)) "git config --global user.name ..." }
Check "codex CLI" (Has codex) "npm i -g @openai/codex; codex login"
Check "claude CLI" (Has claude) "Claude Code"
Check "agy (Antigravity)" (Has agy) "необязательно"
Check "node/npm" (Has npm) "нужен для установки codex"
Check "docker (необязательно)" (Has docker) "не обязательно: деплой по Dockerfile идёт на хостинге"
Check "OPENAI_API_KEY в окружении или .env" ($env:OPENAI_API_KEY -or ((Test-Path .env) -and (Select-String -Quiet "OPENAI_API_KEY=sk" .env))) "ключ выдадут/свой; без него MOCK=1"
try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 https://api.openai.com/v1/models; $net = $true } catch { $net = $_.Exception.Response -ne $null }
Check "доступ к api.openai.com" $net "нет сети или блок"

if ($Wheels -and (Has python)) {
  Write-Host "Скачиваю пакеты в .\wheels (для офлайн-установки: pip install --no-index -f wheels -r requirements.txt)"
  python -m pip download -r requirements.txt -d wheels
}
Write-Host "`nИтого: OK=$ok, проблем=$bad"
