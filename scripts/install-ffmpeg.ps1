<#
.SYNOPSIS
    Install FFmpeg via winget (Windows 11)
#>

param(
    [switch]$Force
)

# Check if ffmpeg already exists
$ffmpegPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
$ffprobePath = (Get-Command ffprobe -ErrorAction SilentlyContinue).Source

if ($ffmpegPath -and $ffprobePath -and -not $Force) {
    Write-Host "FFmpeg already installed at: $ffmpegPath" -ForegroundColor Green
    exit 0
}

Write-Host "Installing FFmpeg via winget..." -ForegroundColor Yellow

# Install Gyan.FFmpeg (official FFmpeg builds for Windows)
try {
    winget install --id Gyan.FFmpeg --silent --accept-source-agreements --accept-package-agreements
}
catch {
    Write-Host "winget install failed. Trying Chocolatey..." -ForegroundColor Yellow
    try {
        choco install ffmpeg -y
    }
    catch {
        Write-Host "Chocolatey install failed. Please install FFmpeg manually from https://ffmpeg.org/download.html" -ForegroundColor Red
        exit 1
    }
}

# Verify installation
$ffmpegPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
$ffprobePath = (Get-Command ffprobe -ErrorAction SilentlyContinue).Source

if ($ffmpegPath -and $ffprobePath) {
    Write-Host "FFmpeg installed successfully at: $ffmpegPath" -ForegroundColor Green
    & ffmpeg -version
    exit 0
}
else {
    Write-Host "FFmpeg installation verification failed. You may need to restart your shell." -ForegroundColor Red
    exit 1
}