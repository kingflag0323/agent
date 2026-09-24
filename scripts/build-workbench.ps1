param([string]$Python='python',[string]$Output='')
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $PSScriptRoot
if(-not $Output){$Output=Join-Path $Root 'release-workbench'}
$Output=[IO.Path]::GetFullPath($Output)
Push-Location (Join-Path $Root 'workbench')
try {
 & npm.cmd ci
 if($LASTEXITCODE -ne 0){throw 'npm ci failed'}
 & npm.cmd run build
 if($LASTEXITCODE -ne 0){throw 'React build failed'}
 $Archive=(& node scripts/download-runtime.mjs | Select-Object -Last 1)
 if($LASTEXITCODE -ne 0 -or -not (Test-Path $Archive)){throw 'Electron runtime download failed'}
} finally {Pop-Location}
Push-Location $Root
try {
 & $Python -m PyInstaller --noconfirm --clean --distpath (Join-Path $Output 'sidecar') --workpath (Join-Path $Root 'build-workbench') desktop/Sidecar.spec
 if($LASTEXITCODE -ne 0){throw 'Python sidecar build failed'}
 $Target=Join-Path $Output 'DoublePupil'
 New-Item -ItemType Directory -Force $Target | Out-Null
 Expand-Archive -Path $Archive -DestinationPath $Target -Force
 Move-Item (Join-Path $Target 'electron.exe') (Join-Path $Target 'DoublePupil.exe') -Force
 $App=Join-Path $Target 'resources\app'
 New-Item -ItemType Directory -Force $App | Out-Null
 Copy-Item workbench/dist,workbench/electron $App -Recurse -Force
 '{"name":"double-pupil","version":"0.4.0","main":"electron/main.cjs","license":"GPL-3.0-only"}' | Set-Content (Join-Path $App 'package.json') -Encoding UTF8
 $Backend=Join-Path $Target 'resources\backend'
 New-Item -ItemType Directory -Force $Backend | Out-Null
 Copy-Item (Join-Path $Output 'sidecar\sentinel-backend\*') $Backend -Recurse -Force
 Copy-Item workbench/LICENSE (Join-Path $Target 'LICENSE-DOUBLE-PUPIL-GPL3.txt')
 Copy-Item workbench/UPSTREAM.md,THIRD_PARTY_NOTICES.md $Target
 Write-Output "Ready: $Target\DoublePupil.exe"
} finally {Pop-Location}
