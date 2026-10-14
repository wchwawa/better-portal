param(
    [switch]$SetupOnly,
    [switch]$Demo,
    [switch]$NoPause
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot

function Invoke-PythonProbe {
    param([string]$Executable, [string[]]$Arguments)
    # Missing interpreters and optional drivers are expected during first setup.
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& $Executable @Arguments 2>$null)
        if ($LASTEXITCODE -eq 0) { return $output }
    } catch { }
    return $null
}

function Resolve-SupportedPython {
    param([string]$Executable, [string[]]$Prefix = @())
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }
    $output = @(Invoke-PythonProbe $Executable ($Prefix + @((Join-Path $script:ProjectRoot 'tools\windows_runtime.py'), 'python')))
    if ($output.Count -gt 0 -and $output[-1] -and (Test-Path -LiteralPath ([string]$output[-1]) -PathType Leaf)) {
        return [string]$output[-1]
    }
    return $null
}

function Find-SupportedPython {
    $candidates = @()
    foreach ($name in @('python.exe', 'python3.exe')) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') {
            $candidates += $command.Source
        }
    }
    foreach ($base in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore')) {
        foreach ($version in @(Get-ChildItem $base -ErrorAction SilentlyContinue)) {
            $install = Get-Item ($version.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
            if ($install) {
                $exe = $install.GetValue('ExecutablePath')
                if ($exe) { $candidates += $exe }
                $directory = $install.GetValue('')
                if ($directory) { $candidates += (Join-Path $directory 'python.exe') }
            }
        }
    }
    foreach ($version in @('314', '313', '312', '311', '310')) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python$version\python.exe")
        $candidates += (Join-Path $env:ProgramFiles "Python$version\python.exe")
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        $python = Resolve-SupportedPython $candidate
        if ($python) { return $python }
    }
    # The classic launcher supports existing installations outside standard paths.
    # Skip Store aliases so a discovery probe cannot start a Store installation.
    $launcher = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($launcher -and $launcher.Source -notlike '*\Microsoft\WindowsApps\*') {
        foreach ($version in @('3.14', '3.13', '3.12', '3.11', '3.10')) {
            $python = Resolve-SupportedPython $launcher.Source @("-$version")
            if ($python) { return $python }
        }
    }
    return $null
}

function Wait-ForInstallation {
    param([string]$Url, [string]$Instructions)
    Write-Host $Instructions -ForegroundColor Yellow
    Write-Host "Official download: $Url"
    Start-Process -FilePath $Url | Out-Null
    $null = Read-Host 'Finish the installation, then press Enter here to continue (Ctrl+C cancels)'
}

function Install-Python {
    $winget = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host 'Installing Python 3.14 with Windows Package Manager...'
        & $winget.Source install --id Python.Python.3.14 --exact --source winget `
            --scope user --architecture x64 --silent --accept-package-agreements --accept-source-agreements | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw 'Python installation did not finish. Read the WinGet error above, then reopen Start-Windows.cmd to retry.'
        }
    } else {
        Wait-ForInstallation 'https://www.python.org/downloads/windows/' `
            'Windows Package Manager is unavailable. Install Python 3.14 using its Windows installer (64-bit).'
    }
    # Read registry/installation paths again; the current Terminal's PATH may be stale.
    $python = Find-SupportedPython
    if (-not $python) {
        throw 'Python 3.10-3.14 (x86-64) could not be found. Finish installing Python 3.14, then reopen Start-Windows.cmd.'
    }
    return $python
}

function Test-Dependencies {
    param([string]$Python)
    $output = @(Invoke-PythonProbe $Python @((Join-Path $script:ProjectRoot 'tools\windows_runtime.py'), 'dependencies'))
    return ($output -contains 'DEPENDENCIES_READY')
}

function Test-Npcap {
    param([string]$Python)
    $output = @(Invoke-PythonProbe $Python @((Join-Path $script:ProjectRoot 'tools\windows_runtime.py'), 'npcap'))
    return ($output -contains 'NPCAP_READY')
}

function Prepare-Environment {
    Write-Host '[1/3] Checking Python...' -ForegroundColor Cyan
    $venv = Join-Path $script:ProjectRoot '.venv'
    $python = Resolve-SupportedPython (Join-Path $venv 'Scripts\python.exe')
    if (-not $python) {
        $base = Find-SupportedPython
        if (-not $base) { $base = Install-Python }
        Write-Host 'Preparing the local application environment...'
        & $base -m venv $venv | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'The local Python environment could not be created. Reopen Start-Windows.cmd to retry.' }
        $python = Resolve-SupportedPython (Join-Path $venv 'Scripts\python.exe')
        if (-not $python) { throw 'The local Python environment is incomplete. Read the error above before retrying.' }
    }

    Write-Host '[2/3] Checking application dependencies...' -ForegroundColor Cyan
    if (-not (Test-Dependencies $python)) {
        & $python -m ensurepip --upgrade | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Python package setup failed. Reopen Start-Windows.cmd to retry.' }
        & $python -m pip install --disable-pip-version-check -r (Join-Path $script:ProjectRoot 'requirements.txt') | Out-Host
        if ($LASTEXITCODE -ne 0 -or -not (Test-Dependencies $python)) {
            throw 'Dependencies are not ready. Check your Internet connection and the error above, then reopen Start-Windows.cmd.'
        }
    }

    Write-Host '[3/3] Checking the Npcap network driver...' -ForegroundColor Cyan
    if ($Demo) {
        Write-Host 'Demo mode: no network driver or administrator access is needed.'
    } elseif (-not (Test-Npcap $python)) {
        Wait-ForInstallation 'https://npcap.com/#download' `
            'Install Npcap from its official page. Leave WinPcap compatibility mode unchecked; Wi-Fi monitor mode is not needed. Accept its installer permission prompt. If it asks for a restart, restart and reopen Start-Windows.cmd.'
        if (-not (Test-Npcap $python)) {
            throw 'Npcap is not available yet. Finish its installation or requested restart, then reopen Start-Windows.cmd.'
        }
    }
    return $python
}

function Invoke-QuickStart {
    $lock = $null
    try {
        if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitOperatingSystem) {
            throw 'Use this launcher on native 64-bit Windows 10 or 11.'
        }
        $architecture = $env:PROCESSOR_ARCHITEW6432
        if (-not $architecture) { $architecture = $env:PROCESSOR_ARCHITECTURE }
        if ($architecture -ne 'AMD64') { throw 'This quick start currently supports x64 Windows PCs. Native ARM64 is not yet supported.' }
        foreach ($name in @('requirements.txt', 'portal_windows_launcher.py', 'portal_tui.py', 'tools\windows_runtime.py')) {
            if (-not (Test-Path -LiteralPath (Join-Path $script:ProjectRoot $name) -PathType Leaf)) {
                throw 'Extract the whole Better Portal ZIP first, then open Start-Windows.cmd from the extracted folder.'
            }
        }
        try {
            $lock = [IO.File]::Open((Join-Path $script:ProjectRoot '.windows-setup.lock'),
                [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        } catch {
            throw 'Another setup window may be open, or this folder is not writable. Close the other setup, or extract Better Portal into a folder you own, then retry.'
        }
        $env:PYTHONUTF8 = '1'
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $OutputEncoding = [Console]::OutputEncoding
        $python = Prepare-Environment
        $lock.Dispose()
        $lock = $null
        if ($SetupOnly) {
            Write-Host 'Setup complete. Double-click Start-Windows.cmd whenever you want to play.' -ForegroundColor Green
            if (-not $NoPause) { $null = Read-Host 'Press Enter to close' }
            return 0
        }
        Write-Host 'Opening Better Portal...' -ForegroundColor Green
        # Inherit the real console. Piping Python output would make curses see a
        # non-interactive terminal. Windows paths cannot contain a double quote.
        $arguments = @('"' + (Join-Path $script:ProjectRoot 'portal_windows_launcher.py') + '"')
        if ($Demo) { $arguments += '--demo' }
        $process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $script:ProjectRoot `
            -NoNewWindow -Wait -PassThru
        return $process.ExitCode
    } catch {
        Write-Host "`nSetup stopped: $($_.Exception.Message)" -ForegroundColor Yellow
        if (-not $NoPause) { $null = Read-Host 'Press Enter to close' }
        return 2
    } finally {
        if ($lock) { $lock.Dispose() }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    exit (Invoke-QuickStart)
}
