$pythonPath = "C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$scriptPath = "D:\project\HKStock\app.py"
$workDir    = "D:\project\HKStock"
$taskName   = "HKStockMonitor"

# Fix: use actual path
$scriptPath = "D:\project\個股監測\app.py"
$workDir    = "D:\project\個股監測"

$action   = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory $workDir
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "Administrator" -RunLevel Highest

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "HK Stock Monitor - auto update at 16:30 HKT" -Force

Write-Host "Task registered: $taskName"
Write-Host "Starting task now..."
Start-ScheduledTask -TaskName $taskName
Start-Sleep 3
Write-Host "Done. Open browser: http://localhost:5000"
