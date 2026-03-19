$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$dateStamp = Get-Date -Format "yyyy-MM-dd"
$cacheRoot = Join-Path $root "cache"
$dailyCacheRoot = Join-Path $cacheRoot $dateStamp
$tempDir = Join-Path $dailyCacheRoot "temp"
$pyInstallerCacheDir = Join-Path $dailyCacheRoot "pyinstaller"
$pyCacheDir = Join-Path $dailyCacheRoot "pycache"

New-Item -ItemType Directory -Force $tempDir, $pyInstallerCacheDir, $pyCacheDir | Out-Null

$env:TMP = $tempDir
$env:TEMP = $tempDir
$env:PYINSTALLER_CONFIG_DIR = $pyInstallerCacheDir
$env:PYTHONPYCACHEPREFIX = $pyCacheDir

python -m pip install --user --progress-bar off --disable-pip-version-check --no-input pyinstaller

if (Test-Path "$root\dist\ImageGridViewer.exe") {
    Remove-Item "$root\dist\ImageGridViewer.exe" -Force
}

python -m PyInstaller --noconfirm --clean --onefile --windowed --name ImageGridViewer `
  --exclude-module numpy `
  --exclude-module numpy_distutils `
  --exclude-module matplotlib `
  --exclude-module tkinter `
  --exclude-module unittest `
  --exclude-module pytest `
  --exclude-module PIL.ImageQt `
  --exclude-module PIL.ImageTk `
  --exclude-module PIL.ImageGrab `
  .\app\main.py

Write-Host ""
Write-Host "Build complete."
Write-Host "Executable: $root\dist\ImageGridViewer.exe"
Write-Host "Cache: $dailyCacheRoot"
