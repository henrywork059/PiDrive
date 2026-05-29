<#
Build piTrainer as a Windows one-folder EXE using PyInstaller.

Run from PowerShell:

    cd C:\Users\henry_sik0ar\Downloads\PiTrainer\PiDrive\piTrainer
    ..\..\.venv\Scripts\Activate.ps1   # adjust if your venv is elsewhere
    powershell -ExecutionPolicy Bypass -File .\PACKAGING\build_windows_onedir.ps1

Output:
    dist_exe\PiTrainer\PiTrainer.exe
    dist_exe\PiTrainer_win_onedir.zip
#>

param(
    [switch]$SkipInstall,
    [switch]$Console
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

if (-not (Test-Path ".\main.py")) {
    throw "This script must be inside the piTrainer component folder. Missing main.py at: $ProjectRoot"
}

Write-Host "PiTrainer one-folder EXE build" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Python: $(python --version)"

if (-not $SkipInstall) {
    Write-Host "Installing/updating PyInstaller in the active environment..." -ForegroundColor Cyan
    python -m pip install --upgrade pyinstaller
}

$env:PITRAINER_CONSOLE = if ($Console) { "1" } else { "0" }

$DistPath = Join-Path $ProjectRoot "dist_exe"
$WorkPath = Join-Path $ProjectRoot "build_exe"
$SpecPath = Join-Path $ProjectRoot "PACKAGING\piTrainer_onedir.spec"

if (Test-Path $DistPath) { Remove-Item $DistPath -Recurse -Force }
if (Test-Path $WorkPath) { Remove-Item $WorkPath -Recurse -Force }

Write-Host "Building one-folder EXE. This can take several minutes with TensorFlow..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm --distpath $DistPath --workpath $WorkPath $SpecPath

$AppDir = Join-Path $DistPath "PiTrainer"
$ExePath = Join-Path $AppDir "PiTrainer.exe"
if (-not (Test-Path $ExePath)) {
    throw "Build finished but PiTrainer.exe was not found at: $ExePath"
}

$RunBat = Join-Path $AppDir "Run_PiTrainer.bat"
@"
@echo off
cd /d "%~dp0"
start "" "%~dp0PiTrainer.exe"
"@ | Set-Content -Path $RunBat -Encoding ASCII

$ZipPath = Join-Path $DistPath "PiTrainer_win_onedir.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -Force

Write-Host "" 
Write-Host "Build complete." -ForegroundColor Green
Write-Host "App folder: $AppDir"
Write-Host "Launcher:   $ExePath"
Write-Host "Zip file:   $ZipPath"
Write-Host "" 
Write-Host "For normal use, open dist_exe\PiTrainer\PiTrainer.exe or Run_PiTrainer.bat." -ForegroundColor Green
Write-Host "For sharing/copying, send dist_exe\PiTrainer_win_onedir.zip." -ForegroundColor Green
