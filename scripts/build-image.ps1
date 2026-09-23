param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^(docker\.io|ghcr\.io)/[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$')]
    [string]$Image,
    [switch]$Push
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$dirty = git status --porcelain -- app requirements.txt Dockerfile data/samples .dockerignore
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect source status' }
if ($dirty) { throw 'Commit application changes first so the image tag identifies its source' }
$revision = git rev-parse --short=12 HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source revision' }
$reference = "$Image`:$revision"
docker build --platform linux/amd64 --label "org.opencontainers.image.revision=$revision" -t $reference .
if ($LASTEXITCODE -ne 0) { throw 'Image build failed' }
if ($Push) {
    # Create a PRIVATE repository and run docker login before using -Push.
    # This script never changes registry visibility or stores credentials.
    docker push $reference
    if ($LASTEXITCODE -ne 0) { throw 'Image push failed; check registry login and repository permissions' }
}
Write-Output "Render Existing Image: $reference"
if (-not $Push) { Write-Output 'Built locally only. Registry upload has not been performed.' }
