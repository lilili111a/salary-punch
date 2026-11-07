@echo off
cd /d "%~dp0dist\SalaryPunch"
if not exist SalaryPunch.exe (
  echo 请先运行 build_exe.ps1 打包
  pause
  exit /b 1
)
start "" "%~dp0dist\SalaryPunch\SalaryPunch.exe"
