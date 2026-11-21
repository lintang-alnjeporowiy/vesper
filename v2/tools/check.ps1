# Cek satu pintu untuk TPT Planner v2: engine (ruff + pytest) dan web (tsc + oxlint + build).
# Jalankan dari mana saja:  powershell -File v2\tools\check.ps1   (tambah -Install untuk instalasi bersih)
param([switch]$Install)

$ErrorActionPreference = 'Stop'
$v2 = Split-Path -Parent $PSScriptRoot
$failed = @()

function Invoke-Step([string]$Name, [scriptblock]$Body) {
    Write-Host "`n== $Name" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) { $script:failed += $Name; Write-Host "GAGAL: $Name" -ForegroundColor Red }
}

Push-Location $v2
try {
    if ($Install -or -not (Test-Path 'engine\.venv')) {
        Invoke-Step 'engine: uv sync' { uv sync --project engine }
    }
    if ($Install -or -not (Test-Path 'web\node_modules')) {
        Invoke-Step 'web: npm ci' { npm --prefix web ci }
    }
    Invoke-Step 'engine: ruff' { uv run --project engine ruff check --config engine/pyproject.toml engine tools }
    Invoke-Step 'engine: pytest' { uv run --project engine pytest engine/tests -q }
    Invoke-Step 'web: tsc + oxlint + build' { npm --prefix web run check }
}
finally {
    Pop-Location
}

if ($failed.Count -gt 0) {
    Write-Host "`nGagal: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "`nSemua cek lulus." -ForegroundColor Green
