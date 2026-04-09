$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$dateStamp = Get-Date -Format "yyyy-MM-dd"
$venvPath = Join-Path $projectRoot ".venv-build"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$cacheRoot = Join-Path $projectRoot "cache"
$dailyCacheRoot = Join-Path $cacheRoot $dateStamp
$tempDir = Join-Path $dailyCacheRoot "temp"
$pipCacheDir = Join-Path $dailyCacheRoot "pip-cache"
$pyInstallerCacheDir = Join-Path $dailyCacheRoot "pyinstaller"
$pyCacheDir = Join-Path $dailyCacheRoot "pycache"

Set-Location $projectRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "The 'py' launcher was not found. Install a python.org Python first."
}

if (Test-Path $venvPath) {
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

py -3.10 -m venv $venvPath

New-Item -ItemType Directory -Force $tempDir, $pipCacheDir, $pyInstallerCacheDir, $pyCacheDir | Out-Null

$env:TMP = $tempDir
$env:TEMP = $tempDir
$env:PIP_CACHE_DIR = $pipCacheDir
$env:PYINSTALLER_CONFIG_DIR = $pyInstallerCacheDir
$env:PYTHONPYCACHEPREFIX = $pyCacheDir

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install --upgrade pyinstaller pillow pyside6

$distExe = Join-Path $projectRoot "dist\ImageGridViewer.exe"

if (Test-Path $distExe) {
    Remove-Item -LiteralPath $distExe -Force
}

& $venvPython -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name ImageGridViewer `
  --runtime-hook "$projectRoot\pyinstaller_runtime_env.py" `
  --hidden-import PySide6.QtCore `
  --hidden-import PySide6.QtGui `
  --hidden-import PySide6.QtWidgets `
  --exclude-module PySide6.QtQml `
  --exclude-module PySide6.QtQmlCore `
  --exclude-module PySide6.QtQmlModels `
  --exclude-module PySide6.QtQuick `
  --exclude-module PySide6.QtQuickControls2 `
  --exclude-module PySide6.QtQuickWidgets `
  --exclude-module PySide6.QtWebEngineCore `
  --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.QtWebChannel `
  --exclude-module PySide6.QtPdf `
  --exclude-module PySide6.QtPdfWidgets `
  --exclude-module PySide6.QtMultimedia `
  --exclude-module PySide6.QtMultimediaWidgets `
  --exclude-module PySide6.QtCharts `
  --exclude-module PySide6.Qt3DCore `
  --exclude-module PySide6.Qt3DRender `
  --exclude-module PySide6.Qt3DInput `
  "$projectRoot\app\main.py"

Write-Host ""
Write-Host "Build complete."
Write-Host "Executable: $distExe"
Write-Host "Cache: $dailyCacheRoot"
