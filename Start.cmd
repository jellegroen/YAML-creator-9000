@echo off
rem Hide command echo and keep variables local to this launcher.
setlocal
rem Change to the folder containing this launcher, even on a different drive.
cd /d "%~dp0"
rem Prefer the Python runtime bundled with Codex on this computer.
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "%~dp0converter.pyw"
  if errorlevel 1 pause
  rem Stop here after running the bundled runtime; do not launch a second copy.
  exit /b
)
rem Otherwise use whichever Python is available on PATH.
python "%~dp0converter.pyw"
rem If launching fails, keep the terminal open so the user can read the error.
if errorlevel 1 (
  echo.
  echo Could not start. Install Python 3 with Tcl/Tk support from python.org.
  echo Enable Add Python to PATH during installation, then try again.
  pause
)
