<#
.SYNOPSIS
    Verify output clips meet quality criteria
    Usage: .\verify.ps1 <job_id>
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$JobId
)

$projectRoot = "D:\AI\Clipper"
$jobDir = "$projectRoot\api\storage\jobs\$JobId"
$clipsDir = "$jobDir\clips"
$clipsMeta = "$jobDir\clips.json"

if (-not (Test-Path $jobDir)) {
    Write-Host "Job directory not found: $jobDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $clipsMeta)) {
    Write-Host "clips.json not found" -ForegroundColor Red
    exit 1
}

$clips = Get-Content $clipsMeta | ConvertFrom-Json
$errors = 0
$warnings = 0

function Check-Ffprobe {
    param([string]$VideoPath, [string]$Label)
    $cmd = "ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,bit_rate -of json `"$VideoPath`""
    $result = Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[$Label] ffprobe failed" -ForegroundColor Red
        $errors++
        return $null
    }
    return $result | ConvertFrom-Json
}

function Check-FfprobeAudio {
    param([string]$VideoPath, [string]$Label)
    $cmd = "ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,bit_rate -of json `"$VideoPath`""
    $result = Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[$Label] ffprobe audio failed" -ForegroundColor Red
        $errors++
        return $null
    }
    return $result | ConvertFrom-Json
}

Write-Host "Verifying job: $JobId" -ForegroundColor Cyan
Write-Host "Found $($clips.Count) clips" -ForegroundColor Cyan
Write-Host ""

foreach ($clip in $clips) {
    $clipPath = "$clipsDir\$($clip.clip_id).mp4"
    $label = $clip.clip_id

    if (-not (Test-Path $clipPath)) {
        Write-Host "[$label] File not found: $clipPath" -ForegroundColor Red
        $errors++
        continue
    }

    Write-Host "[$label] Checking..." -ForegroundColor Yellow

    # Video stream
    $videoInfo = Check-Ffprobe $clipPath $label
    if ($videoInfo -and $videoInfo.streams.Count -gt 0) {
        $s = $videoInfo.streams[0]
        $codec = $s.codec_name
        $width = $s.width
        $height = $s.height
        $fpsStr = $s.r_frame_rate
        $bitrate = [int]$s.bit_rate

        # Parse FPS
        if ($fpsStr -match '(\d+)/(\d+)') {
            $fps = [int]$matches[1] / [int]$matches[2]
        } else {
            $fps = 0
        }

        # Check H.264
        if ($codec -ne 'h264') {
            Write-Host "  [$label] Codec: $codec (expected h264)" -ForegroundColor Red
            $errors++
        } else {
            Write-Host "  [$label] Codec: $codec ��" -ForegroundColor Green
        }

        # Check resolution 720x1280 (9:16)
        if ($width -ne 720 -or $height -ne 1280) {
            Write-Host "  [$label] Resolution: ${width}x${height} (expected 720x1280)" -ForegroundColor Red
            $errors++
        } else {
            Write-Host "  [$label] Resolution: ${width}x${height} ��" -ForegroundColor Green
        }

        # Check FPS 24-60
        if ($fps -lt 24 -or $fps -gt 60) {
            Write-Host "  [$label] FPS: $fps (expected 24-60)" -ForegroundColor Red
            $errors++
        } else {
            Write-Host "  [$label] FPS: $fps ��" -ForegroundColor Green
        }

        # Check bitrate >= 4 Mbps
        $bitrateMbps = $bitrate / 1_000_000
        if ($bitrateMbps -lt 4) {
            Write-Host "  [$label] Bitrate: {0:N1} Mbps (expected >= 4 Mbps)" -f $bitrateMbps -ForegroundColor Red
            $errors++
        } else {
            Write-Host "  [$label] Bitrate: {0:N1} Mbps ��" -f $bitrateMbps -ForegroundColor Green
        }
    }

    # Audio stream
    $audioInfo = Check-FfprobeAudio $clipPath $label
    if ($audioInfo -and $audioInfo.streams.Count -gt 0) {
        $s = $audioInfo.streams[0]
        $acodec = $s.codec_name
        $abitrate = [int]$s.bit_rate

        if ($acodec -ne 'aac') {
            Write-Host "  [$label] Audio codec: $acodec (expected aac)" -ForegroundColor Red
            $errors++
        } else {
            Write-Host "  [$label] Audio codec: $acodec ��" -ForegroundColor Green
        }

        $abitrateKbps = $abitrate / 1000
        if ($abitrateKbps -lt 128) {
            Write-Host "  [$label] Audio bitrate: {0:N0} kbps (expected >= 128 kbps)" -f $abitrateKbps -ForegroundColor Yellow
            $warnings++
        } else {
            Write-Host "  [$label] Audio bitrate: {0:N0} kbps ��" -f $abitrateKbps -ForegroundColor Green
        }
    }

    # Duration check
    if ($clip.duration -gt 60) {
        Write-Host "  [$label] Duration: $($clip.duration)s (exceeds 60s)" -ForegroundColor Yellow
        $warnings++
    } else {
        Write-Host "  [$label] Duration: $($clip.duration)s ��" -ForegroundColor Green
    }

    Write-Host ""
}

# Summary
Write-Host "=== Verification Summary ===" -ForegroundColor Cyan
Write-Host "Clips checked: $($clips.Count)"
Write-Host "Errors: $errors" -ForegroundColor $(if ($errors -gt 0) { 'Red' } else { 'Green' })
Write-Host "Warnings: $warnings" -ForegroundColor $(if ($warnings -gt 0) { 'Yellow' } else { 'Green' })

if ($errors -gt 0) {
    exit 1
}
exit 0