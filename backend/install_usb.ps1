$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot
Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\venv\Scripts\python.exe" -c "import read_esp32"
if ($LASTEXITCODE) { throw "The USB reader Python environment needs repair." }
$startup = [Environment]::GetFolderPath("Startup")
$linkFile = Join-Path $startup "MechGuard USB.lnk"
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($linkFile)
$link.TargetPath = (Get-Command powershell.exe).Source
$link.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $PSScriptRoot + '\watch_usb.ps1"'
$link.WorkingDirectory = $root
$link.WindowStyle = 7
$link.Save()
Start-Process -FilePath $link.TargetPath -ArgumentList $link.Arguments -WindowStyle Hidden
Set-Location -LiteralPath $root
docker compose up -d --build --wait
if ($LASTEXITCODE) { throw "Start Docker Desktop, wait for its engine, then double-click setup again." }
Start-Process "http://localhost:5173"
