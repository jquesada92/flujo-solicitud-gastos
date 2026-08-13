$ErrorActionPreference = 'Stop'

$workspace = Split-Path -Parent $PSScriptRoot
$previewEnv = Join-Path $workspace '.env.preview'

if (-not (Test-Path -LiteralPath $previewEnv)) {
    throw 'No existe .env.preview. El ambiente preview no parece estar configurado.'
}

& docker compose `
    -p flujo-gastos-preview `
    --env-file $previewEnv `
    -f (Join-Path $workspace 'docker-compose.yml') `
    -f (Join-Path $workspace 'docker-compose.preview.yml') `
    down

if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo detener el ambiente preview.'
}
