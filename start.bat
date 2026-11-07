@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM 若已在跑则跳过
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"name='python.exe' OR name='pythonw.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'salary-punch\\\\run\.py' }; if ($p) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [salary-punch] already running, skip
  exit /b 0
)

set "PY="
where pythonw >nul 2>&1
if not errorlevel 1 set "PY=pythonw"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo [错误] 未找到 Python
  pause
  exit /b 1
)

start "薪资打卡器" /min "%PY%" "%~dp0run.py" %*
endlocal
