$ErrorActionPreference = 'Stop'
# Starting Harness starts only the lightweight control panel, never inference.
if (-not (Get-CimInstance Win32_Process -Filter "Name='wsl.exe'" | Where-Object { $_.CommandLine -like '*sleep infinity*' })) {
    Start-Process -FilePath 'wsl.exe' -ArgumentList '-d','Ubuntu-24.04','--','sleep','infinity' -WindowStyle Hidden
}
wsl -d Ubuntu-24.04 -- systemctl --user start workbench-ui.service
if ($LASTEXITCODE -ne 0) { throw 'Harness could not start. Check the workbench-ui service.' }
$panelReady = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8787/api/status' -TimeoutSec 2
        if ($response.StatusCode -eq 200) { $panelReady = $true; break }
    } catch { Start-Sleep -Milliseconds 250 }
}
if (-not $panelReady) { throw 'Harness did not become ready. Check the workbench-ui service.' }
Start-Process 'http://127.0.0.1:8787'
