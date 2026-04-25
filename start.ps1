Write-Host "Starting Idea Refinery..."
$process = Start-Process -FilePath python -ArgumentList @(
    '-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000'
) -PassThru
Start-Sleep -Seconds 3
Start-Process "http://localhost:8000"
Write-Host "Idea Refinery is running at http://localhost:8000"
Write-Host "Press Enter to stop"
[void](Read-Host)
Stop-Process -Id $process.Id
