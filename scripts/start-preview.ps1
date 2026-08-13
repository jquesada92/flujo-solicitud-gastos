param(
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'

$workspace = Split-Path -Parent $PSScriptRoot
$previewEnv = Join-Path $workspace '.env.preview'
$previewExample = Join-Path $workspace '.env.preview.example'
$composeFiles = @(
    '-f', (Join-Path $workspace 'docker-compose.yml'),
    '-f', (Join-Path $workspace 'docker-compose.preview.yml')
)
$composeBase = @(
    'compose',
    '-p', 'flujo-gastos-preview',
    '--env-file', $previewEnv
) + $composeFiles

if (-not (Test-Path -LiteralPath $previewEnv)) {
    Copy-Item -LiteralPath $previewExample -Destination $previewEnv
    Write-Host 'Se creó .env.preview desde la plantilla.'
}

& docker @composeBase up --build -d
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Compose no pudo iniciar el ambiente preview.'
}

Write-Host 'Esperando la URL temporal de Cloudflare...'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$tunnelUrl = $null

while ((Get-Date) -lt $deadline -and -not $tunnelUrl) {
    $logs = & docker @composeBase logs --no-color tunnel 2>&1 | Out-String
    $match = [regex]::Match($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($match.Success) {
        $tunnelUrl = $match.Value
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $tunnelUrl) {
    throw "Cloudflare no publicó una URL en $TimeoutSeconds segundos. Revisa: docker compose -p flujo-gastos-preview --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml logs tunnel"
}

$envContent = Get-Content -LiteralPath $previewEnv -Raw
if ($envContent -match '(?m)^PUBLIC_URL=.*$') {
    $envContent = [regex]::Replace($envContent, '(?m)^PUBLIC_URL=.*$', "PUBLIC_URL=$tunnelUrl")
} else {
    $envContent = $envContent.TrimEnd() + "`r`nPUBLIC_URL=$tunnelUrl`r`n"
}
Set-Content -LiteralPath $previewEnv -Value $envContent -Encoding utf8

& docker @composeBase up -d --force-recreate backend
if ($LASTEXITCODE -ne 0) {
    throw 'La URL se guardó, pero el backend no pudo recrearse.'
}

Write-Host "Preview disponible en: $tunnelUrl" -ForegroundColor Green
Write-Output $tunnelUrl
