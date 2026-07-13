@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0scripts\install.py" %*
) else (
  where python >nul 2>nul
  if not %errorlevel%==0 (
    echo Python 3 not found. Install it from https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  python "%~dp0scripts\install.py" %*
)
set RESULT=%errorlevel%
pause
exit /b %RESULT%
