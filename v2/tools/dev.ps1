# Jalankan Vesper secara lokal: API FastAPI (uvicorn) di latar belakang + web Vite di jendela ini.
# Pemakaian (dari mana saja):
#   powershell -File v2\tools\dev.ps1                 # API :8000 + web :5173, buka browser
#   powershell -File v2\tools\dev.ps1 -WebPort 5174   # port web lain
#   powershell -File v2\tools\dev.ps1 -NoApi          # web saja (angka hasil = placeholder)
# Ctrl+C menghentikan web sekaligus API.
param(
    [int]$WebPort = 5173,
    [int]$ApiPort = 8000,
    [switch]$NoApi,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$v2 = Split-Path -Parent $PSScriptRoot

function Test-PortBusy([int]$Port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect('127.0.0.1', $Port)
        $c.Close()
        return $true
    } catch {
        return $false
    }
}

foreach ($cmd in 'uv', 'npm') {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "'$cmd' tidak ditemukan di PATH." }
}
if (Test-PortBusy $WebPort) { throw "Port web $WebPort sudah dipakai. Coba -WebPort 5174." }

Push-Location $v2
$api = $null
try {
    # Instalasi pertama kali
    if (-not (Test-Path 'engine\.venv')) { Write-Host '== uv sync (pertama kali)' -ForegroundColor Cyan; uv sync --project engine }
    if (-not (Test-Path 'web\node_modules')) { Write-Host '== npm ci (pertama kali)' -ForegroundColor Cyan; npm --prefix web ci }

    if (-not $NoApi) {
        if (Test-PortBusy $ApiPort) {
            Write-Host "API: port $ApiPort sudah aktif, dipakai apa adanya (tidak dijalankan ulang)." -ForegroundColor Yellow
        } else {
            Write-Host "== API  http://127.0.0.1:$ApiPort/docs" -ForegroundColor Cyan
            $api = Start-Process -FilePath 'uv' -NoNewWindow -PassThru -ArgumentList @(
                'run', '--project', 'engine', 'uvicorn', 'tpt_api.app:app',
                '--host', '127.0.0.1', '--port', "$ApiPort", '--reload', '--reload-dir', 'engine/src')
            $deadline = (Get-Date).AddSeconds(30)
            while (-not (Test-PortBusy $ApiPort)) {
                if ($api.HasExited) { throw 'API gagal start (lihat pesan di atas).' }
                if ((Get-Date) -gt $deadline) { throw "API belum merespons di port $ApiPort setelah 30 detik." }
                Start-Sleep -Milliseconds 300
            }
        }
    }

    $env:TPT_API_URL = "http://127.0.0.1:$ApiPort"
    $url = "http://localhost:$WebPort/"
    Write-Host "== Web  $url   (Ctrl+C untuk berhenti)" -ForegroundColor Cyan
    if (-not $NoBrowser) {
        # buka browser setelah Vite siap, tanpa menahan jendela ini
        Start-Job -ScriptBlock {
            param($u, $p)
            for ($i = 0; $i -lt 60; $i++) {
                try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1', $p); $c.Close(); Start-Process $u; return } catch { Start-Sleep -Milliseconds 500 }
            }
        } -ArgumentList $url, $WebPort | Out-Null
    }
    npm --prefix web run dev -- --port $WebPort --strictPort
}
finally {
    if ($api -and -not $api.HasExited) {
        Write-Host '== Menghentikan API' -ForegroundColor Cyan
        # /T: ikut menghentikan proses anak uvicorn --reload
        taskkill /PID $api.Id /T /F | Out-Null
    }
    Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
    Pop-Location
}
