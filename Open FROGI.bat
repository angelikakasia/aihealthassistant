@echo off
cd /d "%~dp0"
py -3 -m security.login_ui
if errorlevel 1 (
  echo FROGI could not start. Install Python with Tcl/Tk support and try again.
  pause
)
