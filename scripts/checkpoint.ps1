param([Parameter(Mandatory=$true)][int]$Hour, [Parameter(Mandatory=$true)][string]$Result)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Hour -lt 1) { throw 'Hour must be positive' }
$tag = "hour-$Hour"
$existing = git tag --list $tag
if ($existing) { throw "Tag $tag already exists; never overwrite checkpoint history" }
& ./.venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
# Stage reviewed files before invoking; never auto-add unrelated files or secrets.
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { throw 'No staged checkpoint changes' }
git commit -m "[codex] checkpoint $Hour`: $Result"
if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
git tag -a $tag -m $Result
if ($LASTEXITCODE -ne 0) { throw 'Tag failed' }
git push origin HEAD
if ($LASTEXITCODE -ne 0) { throw 'Branch push failed; local checkpoint retained' }
git push origin "refs/tags/$tag"
if ($LASTEXITCODE -ne 0) { throw 'Tag push failed; local tag retained' }
