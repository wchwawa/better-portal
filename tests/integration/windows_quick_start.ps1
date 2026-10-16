# Run the shipped launchers under Windows PowerShell 5.1 in an extracted-folder model.
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage = Join-Path $env:TEMP ("Better Portal's & " + [char]0x5BB6 + ' ' + [guid]::NewGuid().ToString())

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Run-Setup {
    param([int]$ExpectedCode)
    $ErrorActionPreference = 'Continue'
    $lines = @(& (Join-Path $stage 'Start-Windows.cmd') -SetupOnly -Demo -NoPause 2>&1)
    $code = $LASTEXITCODE
    $text = ($lines | ForEach-Object { $_.ToString() }) -join "`n"
    Write-Host $text
    Assert-True ($code -eq $ExpectedCode) "Expected exit $ExpectedCode, got $code"
    if ($ExpectedCode -eq 0) {
        Assert-True ($text.Contains('Setup complete.')) 'Missing completion message'
    } else {
        Assert-True (-not $text.Contains('Setup complete.')) 'Failed setup claimed completion'
    }
}

$oldNoIndex = $env:PIP_NO_INDEX
try {
    $null = New-Item -ItemType Directory -Path $stage
    foreach ($item in @(Get-ChildItem $root -File | Where-Object { $_.Extension -in @('.py', '.cmd') -or $_.Name -eq 'requirements.txt' })) {
        Copy-Item -LiteralPath $item.FullName -Destination $stage
    }
    foreach ($directory in @('tools', 'locales', 'tests\integration')) {
        $null = New-Item -ItemType Directory -Path (Join-Path $stage $directory) -Force
    }
    Copy-Item -Path (Join-Path $root 'tools\windows*') -Destination (Join-Path $stage 'tools')
    Copy-Item -Path (Join-Path $root 'locales\*.json') -Destination (Join-Path $stage 'locales')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'windows_tui_smoke.py') -Destination (Join-Path $stage 'tests\integration')
    $settings = '{"language":"zh-CN","profile":"100"}'
    $config = '{"interface":"saved adapter","ps5_ip":"192.0.2.10","portal_ip":"192.0.2.20"}'
    [IO.File]::WriteAllText((Join-Path $stage 'tui-settings.json'), $settings)
    [IO.File]::WriteAllText((Join-Path $stage 'config.windows.json'), $config)

    # First-install network failure must stop before the app opens, then be retryable.
    $env:PIP_NO_INDEX = '1'
    Run-Setup 2
    $env:PIP_NO_INDEX = $oldNoIndex
    Run-Setup 0

    # A healthy repeat must work without a package index and preserve user settings.
    $env:PIP_NO_INDEX = '1'
    Run-Setup 0
    $requirementsPath = Join-Path $stage 'requirements.txt'
    $requirements = [IO.File]::ReadAllText($requirementsPath)
    [IO.File]::WriteAllText($requirementsPath, 'scapy==0.0.0')
    Run-Setup 2
    [IO.File]::WriteAllText($requirementsPath, $requirements)
    Run-Setup 0
    # Package metadata can survive a missing native module. Repair its files too.
    $native = @(Get-ChildItem (Join-Path $stage '.venv\Lib\site-packages\_curses.*.pyd'))
    Assert-True ($native.Count -ge 1) 'Native curses module was not installed'
    Remove-Item -LiteralPath $native[0].FullName
    $env:PIP_NO_INDEX = $oldNoIndex
    Run-Setup 0
    Assert-True (Test-Path -LiteralPath $native[0].FullName) 'Broken native module was not repaired'
    $env:PIP_NO_INDEX = '1'
    Run-Setup 0
    Assert-True ([IO.File]::ReadAllText((Join-Path $stage 'tui-settings.json')) -eq $settings) 'Language/bitrate changed during setup'
    Assert-True ([IO.File]::ReadAllText((Join-Path $stage 'config.windows.json')) -eq $config) 'Addresses changed during setup'

    $python = Join-Path $stage '.venv\Scripts\python.exe'
    & $python (Join-Path $stage 'tests\integration\windows_tui_smoke.py')
    Assert-True ($LASTEXITCODE -eq 0) 'Installed runtime failed native TUI smoke test'
    & $python (Join-Path $PSScriptRoot 'windows_quick_start_console.py') $stage
    Assert-True ($LASTEXITCODE -eq 0) 'Quick-start console inheritance failed'

    # Exercise driver handling without installing a driver or opening a browser on CI.
    . (Join-Path $stage 'tools\windows-quick-start.ps1') -SetupOnly -NoPause
    $script:DriverChecks = 0
    $script:OpenedUrls = @()
    function Test-Npcap { param($Python) $script:DriverChecks++; return $script:DriverChecks -ge 2 }
    function Wait-ForInstallation { param($Url, $Instructions) $script:OpenedUrls += $Url }
    Assert-True ((Invoke-QuickStart) -eq 0) 'Setup did not continue after driver installation'
    Assert-True ($script:OpenedUrls.Count -eq 1 -and $script:OpenedUrls[0] -eq 'https://npcap.com/#download') 'Unexpected driver download source'
    Assert-True ($script:DriverChecks -eq 2) 'Driver was not rechecked after installation'
    function Test-Npcap { param($Python) return $false }
    Assert-True ((Invoke-QuickStart) -eq 2) 'Missing driver must prevent completion'

    # Contended setup must fail without changing the environment.
    $held = [IO.File]::Open((Join-Path $stage '.windows-setup.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    try { Assert-True ((Invoke-QuickStart) -eq 2) 'Concurrent setup was not blocked' }
    finally { $held.Dispose() }
    Write-Host 'WINDOWS_QUICK_START_PASS: install retry, offline repeat, dependency failure, settings, native UI, console, driver gates, and lock.'
} finally {
    $env:PIP_NO_INDEX = $oldNoIndex
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
