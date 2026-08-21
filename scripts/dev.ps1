<#
.SYNOPSIS
    Start both API and Web dev servers concurrently
#>

param()

# Start API server in background
$apiJob = Start-Job -ScriptBlock {
    Set-Location "D:\AI\Clipper\api"
    $env:PYTHONPATH = "D:\AI\Clipper\api"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Start Web dev server in background
$webJob = Start-Job -ScriptBlock {
    Set-Location "D:\AI\Clipper\web"
    npm run dev
}

Write-Host "API running on http://localhost:8000" -ForegroundColor Green
Write-Host "Web running on http://localhost:5173" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow

try {
    Wait-Job $apiJob, $webJob
}
finally {
    Stop-Job $apiJob, $webJob
    Remove-Job $apiJob, $webJob
}