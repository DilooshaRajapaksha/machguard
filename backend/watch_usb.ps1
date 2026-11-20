param([string]$Port = "COM4", [string]$DeviceId = "ESP32-1")
$ErrorActionPreference = "Stop"
$mutex = New-Object Threading.Mutex($false, "Local\MechGuardUsbWatcher")
if (-not $mutex.WaitOne(0)) { exit }
$worker = $null
try {
    while ($true) {
        $ready = $false
        if ([IO.Ports.SerialPort]::GetPortNames() -contains $Port) {
            try {
                $ready = (Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2).status -eq "ok"
            } catch { $ready = $false }
        }
        if ($worker -and $worker.HasExited) {
            $worker.Dispose()
            $worker = $null
        }
        if ($ready -and -not $worker) {
            $reader = Join-Path $PSScriptRoot "read_esp32.ps1"
            $worker = Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList @(
                "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ('"{0}"' -f $reader),
                "-Port", $Port, "-DeviceId", $DeviceId
            )
        } elseif (-not $ready -and $worker) {
            $worker.Kill()
            $worker.WaitForExit()
        }
        Start-Sleep -Seconds 4
    }
} finally {
    if ($worker -and -not $worker.HasExited) { $worker.Kill() }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
