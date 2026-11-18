param([Parameter(Mandatory)][string]$Port)
$ErrorActionPreference = "Stop"
$serial = [System.IO.Ports.SerialPort]::new($Port, 115200)
try {
    $serial.Open()
    Write-Host "Reading $Port. Press Ctrl+C to stop."
    & { while ($serial.IsOpen) { $serial.ReadLine() } } |
        & "$PSScriptRoot\venv\Scripts\python.exe" -u "$PSScriptRoot\read_esp32.py"
} finally {
    $serial.Dispose()
}
