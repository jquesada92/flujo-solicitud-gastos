param(
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'

$workspace = Split-Path -Parent $PSScriptRoot
$previewEnv = Join-Path $workspace '.env.preview'
$previewExample = Join-Path $workspace '.env.preview.example'
$backendPreviewEnv = Join-Path $workspace 'backend\.env.preview'
$backendPreviewExample = Join-Path $workspace 'backend\.env.preview.example'
$composeFiles = @(
    '-f', (Join-Path $workspace 'docker-compose.yml'),
    '-f', (Join-Path $workspace 'docker-compose.preview.yml')
)
$composeBase = @(
    'compose',
    '-p', 'flujo-gastos-preview',
    '--env-file', $previewEnv
) + $composeFiles

function Get-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    $content = Get-Content -LiteralPath $Path -Raw
    $match = [regex]::Match($content, "(?m)^$([regex]::Escape($Name))=(.*)$")
    if (-not $match.Success) {
        return $null
    }
    return $match.Groups[1].Value.Trim()
}

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $content = Get-Content -LiteralPath $Path -Raw
    $pattern = "(?m)^$([regex]::Escape($Name))=.*$"
    if ($content -match $pattern) {
        $content = [regex]::Replace($content, $pattern, "$Name=$Value")
    } else {
        $content = $content.TrimEnd() + "`r`n$Name=$Value`r`n"
    }
    Set-Content -LiteralPath $Path -Value $content -Encoding utf8
}

if (-not (Test-Path -LiteralPath $previewEnv)) {
    Copy-Item -LiteralPath $previewExample -Destination $previewEnv
    Write-Host 'Se creó .env.preview desde la plantilla.'
}

if (-not (Test-Path -LiteralPath $backendPreviewEnv)) {
    Copy-Item -LiteralPath $backendPreviewExample -Destination $backendPreviewEnv
    Write-Host 'Se creó backend/.env.preview desde la plantilla.'
}

$previewAdminEmail = Get-DotEnvValue -Path $backendPreviewEnv -Name 'ADMIN_EMAIL'
$previewAdminPassword = Get-DotEnvValue -Path $backendPreviewEnv -Name 'ADMIN_PASSWORD'
if (
    [string]::IsNullOrWhiteSpace($previewAdminEmail) -or
    $previewAdminEmail.StartsWith('REPLACE_') -or
    [string]::IsNullOrWhiteSpace($previewAdminPassword) -or
    $previewAdminPassword.StartsWith('REPLACE_') -or
    $previewAdminPassword.Length -lt 16
) {
    throw 'Configura ADMIN_EMAIL y un ADMIN_PASSWORD aleatorio de al menos 16 caracteres en backend/.env.preview antes de publicar el túnel.'
}

# Ensure preview always uses the backend-specific preview file, including when
# an older root .env.preview does not yet define BACKEND_ENV_FILE.
$env:BACKEND_ENV_FILE = './backend/.env.preview'

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

$envContent = Get-Content -LiteralPath $backendPreviewEnv -Raw
if ($envContent -match '(?m)^PUBLIC_URL=.*$') {
    $envContent = [regex]::Replace($envContent, '(?m)^PUBLIC_URL=.*$', "PUBLIC_URL=$tunnelUrl")
} else {
    $envContent = $envContent.TrimEnd() + "`r`nPUBLIC_URL=$tunnelUrl`r`n"
}
Set-Content -LiteralPath $backendPreviewEnv -Value $envContent -Encoding utf8

Set-DotEnvValue -Path $previewEnv -Name 'LOCAL_PUBLIC_URL' -Value $tunnelUrl
Set-DotEnvValue -Path $previewEnv -Name 'LOCAL_CORS_ALLOWED_ORIGINS' -Value $tunnelUrl
Set-DotEnvValue -Path $previewEnv -Name 'LOCAL_EMAIL_MODE' -Value 'console'
& docker @composeBase up -d --force-recreate backend
if ($LASTEXITCODE -ne 0) {
    throw 'La URL se guardó, pero el backend no pudo recrearse.'
}

Write-Host "Preview disponible en: $tunnelUrl" -ForegroundColor Green
Write-Output $tunnelUrl
