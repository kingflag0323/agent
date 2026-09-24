param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& $Python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock -r desktop\requirements.lock pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
Write-Output 'Run start-windows.cmd to launch the native desktop application.'
