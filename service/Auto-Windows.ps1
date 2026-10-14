# Experimental Windows Task Scheduler installation. Run as Administrator.
param([ValidateSet('Menu','Configure','Baseline','Run','Install','Start','Stop','Status','Uninstall')][string]$Action='Menu')
$ErrorActionPreference='Stop'
$Source=Split-Path $PSScriptRoot -Parent
$Target=Join-Path $env:ProgramData 'PortalBitrateAuto'
$Runtime=Join-Path $Target 'runtime'
$TaskName='PortalBitrateAutoPreview'
$LocalPython=Join-Path $Source '.venv\Scripts\python.exe'
$InstalledPython=Join-Path $Target '.venv\Scripts\python.exe'
function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
 & $Exe @Arguments
 if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }
}
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Right-click Auto-Windows.cmd and Run as administrator.' }
if ($Action -eq 'Menu') {
 Write-Host 'Configure, Baseline, Run, Install, Start, Stop, Status, Uninstall'
 $Action=Read-Host 'Command'
}
switch ($Action) {
 'Configure' {
  $Profile=Read-Host 'Profile: 65 (recommended first), 100, or 200'
  Invoke-Checked $LocalPython @((Join-Path $Source 'portal_auto.py'),'configure','--profile',$Profile)
 }
 'Baseline' { Invoke-Checked $LocalPython @((Join-Path $Source 'portal_auto.py'),'baseline') }
 'Run' { Invoke-Checked $LocalPython @((Join-Path $Source 'portal_auto.py'),'run') }
 'Install' {
  if (Test-Path $Target) { throw 'Existing installation found. Stop/uninstall and back up/remove its retained ProgramData directory before reinstalling.' }
  # SYSTEM must not execute a Python interpreter from a user-writable directory.
  $BasePython=(& $LocalPython -c 'import sys; print(sys._base_executable)').Trim()
  if ($LASTEXITCODE -ne 0 -or -not $BasePython.StartsWith($env:ProgramFiles+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Install Python for all users under Program Files, recreate the project .venv, then repeat Configure and Baseline.' }
  Invoke-Checked $LocalPython @((Join-Path $Source 'portal_auto.py'),'verify-baseline')
  if ((Read-Host 'Was picture/control response usable during baseline? Type YES') -cne 'YES') { throw 'Cancelled' }
  New-Item -ItemType Directory -Path $Target | Out-Null
  # Only SYSTEM and Administrators may change executable code or enrollment.
  Invoke-Checked 'icacls.exe' @($Target,'/inheritance:r','/grant:r','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F')
  New-Item -ItemType Directory -Path $Runtime | Out-Null
  $Files=@('portal_auto.py','portal_auto_platform.py','portal_active_probe.py','portal_capture.py','portal_egress_witness.py','portal_windows_network.py','portal_recovery.py','protocol.py','requirements.txt','auto-config.json')
  foreach ($Name in $Files) { Copy-Item (Join-Path $Source $Name) (Join-Path $Target $Name) }
  Copy-Item (Join-Path $Source 'auto-runtime\auto-baseline.json') (Join-Path $Runtime 'auto-baseline.json')
  Invoke-Checked $BasePython @('-m','venv',(Join-Path $Target '.venv'))
  Invoke-Checked $InstalledPython @('-m','pip','install','-r',(Join-Path $Target 'requirements.txt'))
  $Arguments='-u "'+(Join-Path $Target 'portal_auto.py')+'" run --runtime "'+$Runtime+'"'
  $TaskAction=New-ScheduledTaskAction -Execute $InstalledPython -Argument $Arguments -WorkingDirectory $Target
  $Trigger=New-ScheduledTaskTrigger -AtStartup
  $Principal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
  $Settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $Trigger -Principal $Principal -Settings $Settings | Out-Null
  Start-ScheduledTask -TaskName $TaskName
  Write-Host 'Task registered. Wait 15 seconds then use Status; registration alone does not prove relay operation.'
 }
 'Start' {
  Remove-Item (Join-Path $Runtime 'disabled') -ErrorAction SilentlyContinue
  Start-ScheduledTask -TaskName $TaskName
 }
 'Stop' {
  Invoke-Checked $InstalledPython @((Join-Path $Target 'portal_auto.py'),'stop','--runtime',$Runtime)
  for ($i=0; $i -lt 45; $i++) {
   if ((Get-ScheduledTask -TaskName $TaskName).State -ne 'Running') { break }
   Start-Sleep -Seconds 1
  }
  if ((Get-ScheduledTask -TaskName $TaskName).State -eq 'Running') { throw 'Still running. Do not force-kill the guardian. Check recovery status.' }
  Invoke-Checked $InstalledPython @((Join-Path $Target 'portal_auto.py'),'status','--runtime',$Runtime)
 }
 'Status' {
  Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State
  Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object LastRunTime,LastTaskResult
  Invoke-Checked $InstalledPython @((Join-Path $Target 'portal_auto.py'),'status','--runtime',$Runtime)
 }
 'Uninstall' {
  & $PSCommandPath -Action Stop
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Task removed; private files retained at $Target"
 }
 default { throw 'Unknown command' }
}
