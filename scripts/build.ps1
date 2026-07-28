# Local Windows build for smart-convert (PyInstaller onefile).
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/build.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -WithFfmpeg
param(
    [switch]$WithFfmpeg,
    [string]$OutDir = "dist/smart_convert_nvenc-windows-amd64"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Syncing release deps..."
uv sync --group release

Write-Host "Building smart-convert.exe..."
uv run pyinstaller `
    --noconfirm --clean --onefile --name "smart-convert" `
    --manifest packaging/windows/smart-convert.manifest `
    --collect-all customtkinter `
    --collect-data smart_convert_nvenc `
    scripts/pyi_smart_convert.py

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Copy-Item -Force "dist/smart-convert.exe" (Join-Path $OutDir "smart-convert.exe")
Copy-Item -Force "README.md", "LICENSE" $OutDir

if ($WithFfmpeg) {
    Write-Host "Fetching bundled FFmpeg (Git Bash / WSL required for fetch_ffmpeg.sh)..."
    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if (-not $bash) {
        throw "bash not found. Install Git for Windows or omit -WithFfmpeg."
    }
    & bash scripts/fetch_ffmpeg.sh windows-amd64 $OutDir
}

Write-Host "Staged: $OutDir"
Get-ChildItem $OutDir | Format-Table Name, Length
