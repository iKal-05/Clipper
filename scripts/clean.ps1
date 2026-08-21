<#
.SYNOPSIS
    Clean all build artifacts, caches, and temporary files
#>

param(
    [switch]$All
)

$projectRoot = "D:\AI\Clipper"

Write-Host "Cleaning project artifacts..." -ForegroundColor Yellow

# Python caches
$pythonCaches = @(
    "$projectRoot\api\__pycache__",
    "$projectRoot\api\.pytest_cache",
    "$projectRoot\api\.ruff_cache",
    "$projectRoot\api\*.egg-info"
)

foreach ($cache in $pythonCaches) {
    if (Test-Path $cache) {
        Remove-Item -Recurse -Force $cache -ErrorAction SilentlyContinue
        Write-Host "Removed: $cache" -ForegroundColor Gray
    }
}

# Runtime storage
$storagePath = "$projectRoot\api\storage"
if (Test-Path $storagePath) {
    Remove-Item -Recurse -Force $storagePath -ErrorAction SilentlyContinue
    Write-Host "Removed: $storagePath" -ForegroundColor Gray
}

# Node caches
$nodeCaches = @(
    "$projectRoot\web\node_modules",
    "$projectRoot\web\dist",
    "$projectRoot\web\.vite"
)

if ($All) {
    foreach ($cache in $nodeCaches) {
        if (Test-Path $cache) {
            Remove-Item -Recurse -Force $cache -ErrorAction SilentlyContinue
            Write-Host "Removed: $cache" -ForegroundColor Gray
        }
    }
}

# Editor/OS artifacts
$artifacts = @(
    "$projectRoot\.vscode",
    "$projectRoot\.idea",
    "$projectRoot\Thumbs.db",
    "$projectRoot\desktop.ini"
)

foreach ($artifact in $artifacts) {
    if (Test-Path $artifact) {
        Remove-Item -Recurse -Force $artifact -ErrorAction SilentlyContinue
    }
}

Write-Host "Clean complete!" -ForegroundColor Green

if (-not $All) {
    Write-Host "Note: node_modules and web/dist preserved. Use -All to remove them too." -ForegroundColor Yellow
}