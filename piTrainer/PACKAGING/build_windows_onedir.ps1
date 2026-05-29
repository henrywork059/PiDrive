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

function New-ZipWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath,
        [int]$Attempts = 8,
        [int]$DelaySeconds = 4
    )

    for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
        try {
            if (Test-Path $DestinationPath) { Remove-Item $DestinationPath -Force -ErrorAction SilentlyContinue }
            if ($Attempt -gt 1) {
                Write-Host "Retrying zip creation ($Attempt/$Attempts)..." -ForegroundColor Yellow
            }
            Compress-Archive -Path $SourcePath -DestinationPath $DestinationPath -Force -ErrorAction Stop
            return $true
        } catch {
            $Message = $_.Exception.Message
            if ($Attempt -lt $Attempts) {
                Write-Warning "Zip creation failed because a build file may still be locked. Waiting $DelaySeconds seconds. Details: $Message"
                Start-Sleep -Seconds $DelaySeconds
            } else {
                Write-Warning "Zip creation failed after $Attempts attempts. The EXE folder is still usable. Details: $Message"
                return $false
            }
        }
    }
    return $false
}

$ZipPath = Join-Path $DistPath "PiTrainer_win_onedir.zip"
Write-Host "Creating transfer zip. If Windows/antivirus still has build files locked, this step will retry..." -ForegroundColor Cyan
$ZipCreated = New-ZipWithRetry -SourcePath $AppDir -DestinationPath $ZipPath

Write-Host "" 
Write-Host "Build complete." -ForegroundColor Green
Write-Host "App folder: $AppDir"
Write-Host "Launcher:   $ExePath"
if ($ZipCreated -and (Test-Path $ZipPath)) {
    Write-Host "Zip file:   $ZipPath"
} else {
    Write-Host "Zip file:   not created because Windows kept a file locked. Close Explorer/antivirus scan if needed and rerun the script, or copy the app folder directly." -ForegroundColor Yellow
}
Write-Host "" 
Write-Host "For normal use, open dist_exe\PiTrainer\PiTrainer.exe or Run_PiTrainer.bat." -ForegroundColor Green
if ($ZipCreated -and (Test-Path $ZipPath)) {
    Write-Host "For sharing/copying, send dist_exe\PiTrainer_win_onedir.zip." -ForegroundColor Green
} else {
    Write-Host "For sharing/copying right now, copy the whole dist_exe\PiTrainer folder." -ForegroundColor Yellow
}
