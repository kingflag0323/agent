param([string]$Python = 'python', [string]$Output = '')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $Output) { $Output = Join-Path $Root 'release' }
& $Python -m PyInstaller --noconfirm --clean --distpath $Output --workpath (Join-Path $Root 'build') (Join-Path $Root 'desktop\Sentinel.spec')
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
Copy-Item (Join-Path $Root 'README.md') (Join-Path $Output 'Sentinel\README.md') -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root 'THIRD_PARTY_NOTICES.md') (Join-Path $Output 'Sentinel\THIRD_PARTY_NOTICES.md') -ErrorAction SilentlyContinue
Write-Output "Built: $Output\Sentinel\Sentinel.exe"
