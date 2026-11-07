# 打包薪资打卡器为单目录 exe（较 onefile 启动更稳）
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw '未找到 python' }

python -c "import PyInstaller, win32api" 2>$null; if (-not $?) { python -m pip install -q pyinstaller pywin32 pillow }

$dist = Join-Path $PSScriptRoot 'dist\SalaryPunch'

# 先停掉正在跑的，避免占用；并尽量让摸鱼时长已落在 AppData
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and (($_.Name -eq 'SalaryPunch.exe') -or ($_.CommandLine -match 'salary-punch\\run\.py|SalaryPunch\.exe')) } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 400

# 重打包前备份 dist 旁 data（摸鱼统计已迁 AppData，这里只保小说/视频等旁路文件）
$dataBackup = Join-Path $env:TEMP ("SalaryPunch-data-bak-" + [guid]::NewGuid().ToString("N"))
if (Test-Path (Join-Path $dist 'data')) {
  Copy-Item (Join-Path $dist 'data') $dataBackup -Recurse -Force
}
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }

# 托盘/卡片菜单回归，防止再丢托盘右键
python -X utf8 "$(Join-Path $PSScriptRoot 'tools\check_tray_menu.py')"
if (-not $?) { throw 'tray menu regression failed' }

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name SalaryPunch `
  --onedir `
  --icon (Join-Path $PSScriptRoot 'assets\tray.ico') `
  --add-data "assets;assets" `
  --hidden-import salary_punch `
  --hidden-import salary_punch.config `
  --hidden-import salary_punch.config_ui `
  --hidden-import salary_punch.engine `
  --hidden-import salary_punch.phrases `
  --hidden-import salary_punch._period `
  --hidden-import salary_punch.games `
  --hidden-import salary_punch.games.ttt `
  --hidden-import salary_punch.games.gomoku `
  --hidden-import salary_punch.games.shooter `
  --hidden-import salary_punch.games.advice `
  --hidden-import salary_punch.games.novel `
  --hidden-import salary_punch.games.memo `
  --hidden-import salary_punch.games.video `
  --hidden-import salary_punch.games.market `
  --hidden-import cv2 `
  --collect-all cv2 `
  --hidden-import salary_punch.games.muyu `
  --hidden-import salary_punch.games.coin `
  --hidden-import salary_punch.games.dice `
  --hidden-import salary_punch.reminders `
  --hidden-import salary_punch.fish `
  --hidden-import salary_punch.dark_menu `
  --hidden-import salary_punch.ui `
  --hidden-import salary_punch.tray_win `
  --hidden-import salary_punch.punch_ui `
  --hidden-import salary_punch.autostart `
  --collect-all win32com `
  --collect-all pythonwin `
  run.py

# 旁路可写 data：恢复备份；配置以 AppData\SalaryPunch 为准，这里不覆盖摸鱼累计
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'data') | Out-Null
if (Test-Path $dataBackup) {
  Copy-Item (Join-Path $dataBackup '*') (Join-Path $dist 'data') -Recurse -Force
  Remove-Item $dataBackup -Recurse -Force -ErrorAction SilentlyContinue
}
# 仅当 dist data 没有 config 时，从项目 data 拷一份「非摸鱼」默认（仍会被 AppData 迁移逻辑盖过）
$distCfg = Join-Path $dist 'data\config.json'
$cfg = Join-Path $PSScriptRoot 'data\config.json'
if (-not (Test-Path $distCfg) -and (Test-Path $cfg)) {
  Copy-Item $cfg $distCfg -Force
}

# 启动快捷 bat
@"
@echo off
cd /d "%~dp0"
start "" "%~dp0SalaryPunch.exe"
"@ | Set-Content -Encoding Ascii (Join-Path $dist 'start_salarypunch.bat')

Write-Host "OK -> $dist\SalaryPunch.exe"
