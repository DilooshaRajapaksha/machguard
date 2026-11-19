param([Parameter(Mandatory)][string]$Port, [ValidatePattern("^[A-Za-z0-9_-]{1,64}$")][string]$DeviceId)
$ErrorActionPreference = "Stop"
$serial = [System.IO.Ports.SerialPort]::new($Port, 115200)
$serial.ReadTimeout = 1000
$reader = $null
try {
    $serial.Open()
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = "$PSScriptRoot\venv\Scripts\python.exe"
    $start.WorkingDirectory = $PSScriptRoot
    $start.Arguments = "-u read_esp32.py $DeviceId"
    $start.UseShellExecute = $false
    $start.RedirectStandardInput = $true
    $reader = [System.Diagnostics.Process]::Start($start)
    $reader.StandardInput.AutoFlush = $true
    Write-Host "Reading $Port. Press Ctrl+C to stop."
    while ($serial.IsOpen) {
        if ($reader.HasExited) { throw "USB reader exited with code $($reader.ExitCode)." }
        try { $line = $serial.ReadLine() }
        catch [TimeoutException] { continue }
        $reader.StandardInput.WriteLine($line)
    }
} finally {
    $serial.Dispose()
    if ($reader) {
        $reader.StandardInput.Close()
        $reader.WaitForExit()
        $reader.Dispose()
    }
}
