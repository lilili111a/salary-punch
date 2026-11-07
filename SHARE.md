# 薪资打卡器 · 分享包

## 直接运行（推荐）
1. 解压本包
2. 进入 `dist\SalaryPunch`
3. 双击 `SalaryPunch.exe`（或 `start_salarypunch.bat`）

首次运行会按默认配置；正式薪资请右键卡片 → 配置。
配置与摸鱼累计默认写到 `%AppData%\SalaryPunch`（避免覆盖安装包内模板）。

## 源码运行
```bat
pip install -r requirements.txt
python run.py
```

## 重新打包
```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

## 说明
- 已排除个人累计数据、调试日志、小说/视频私货
- `data\config.example.json` 为示例配置
