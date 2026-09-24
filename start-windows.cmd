@echo off
if exist "%~dp0release\DoublePupil\DoublePupil.exe" (
  start "" "%~dp0release\DoublePupil\DoublePupil.exe"
  exit /b 0
)
if exist "%LOCALAPPDATA%\Programs\DoublePupil\DoublePupil.exe" (
  start "" "%LOCALAPPDATA%\Programs\DoublePupil\DoublePupil.exe"
  exit /b 0
)
echo Double Pupil is not built. See README.md or run scripts\build-workbench.ps1.
exit /b 1
