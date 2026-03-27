# Auto-start setup: Flask + ngrok
# Run as Administrator

$pythonPath = "C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$scriptPath = "D:\project\個股監測\app.py"
$ngrokPath  = (Get-Command ngrok -ErrorAction Stop).Source
$ngrokArgs  = "http --url=overprompt-nonabsolutistically-gertrud.ngrok-free.dev 5000"
$workDir    = "D:\project\個股監測"
$principal  = New-ScheduledTaskPrincipal -UserId "Administrator" -RunLevel Highest

# Task 1: Flask
$taskFlask    = "StockMonitor-Flask"
$actionFlask  = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory $workDir
$triggerFlask = New-ScheduledTaskTrigger -AtLogOn
$settingsFlask = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Unregister-ScheduledTask -TaskName $taskFlask -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $taskFlask `
    -Action $actionFlask `
    -Trigger $triggerFlask `
    -Settings $settingsFlask `
    -Principal $principal `
    -Force

Write-Host "[OK] Flask task created" -ForegroundColor Green

# Task 2: ngrok (delayed 10s to let Flask start first)
$taskNgrok    = "StockMonitor-ngrok"
$actionNgrok  = New-ScheduledTaskAction -Execute $ngrokPath -Argument $ngrokArgs
$triggerNgrok = New-ScheduledTaskTrigger -AtLogOn
$triggerNgrok.Delay = "PT10S"
$settingsNgrok = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Unregister-ScheduledTask -TaskName $taskNgrok -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $taskNgrok `
    -Action $actionNgrok `
    -Trigger $triggerNgrok `
    -Settings $settingsNgrok `
    -Principal $principal `
    -Force

Write-Host "[OK] ngrok task created" -ForegroundColor Green
Write-Host ""
Write-Host "URL: https://overprompt-nonabsolutistically-gertrud.ngrok-free.dev" -ForegroundColor Cyan
Write-Host ""

# Start immediately
Write-Host "Starting services now..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $taskFlask
Start-Sleep 5
Start-ScheduledTask -TaskName $taskNgrok
Start-Sleep 3
Write-Host "Done! Open: https://overprompt-nonabsolutistically-gertrud.ngrok-free.dev" -ForegroundColor Green
