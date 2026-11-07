# 薪资打卡器

右下角深色精致悬浮卡片，实时显示今日/本月已赚工资与出勤天数。

## 启动

```bat
cd /d D:\ieswork\salary-punch
start.bat
```

或：

```bat
python run.py
```

可选开机自启：

```powershell
powershell -ExecutionPolicy Bypass -File D:\ieswork\salary-punch\install_autostart.ps1
# 取消：加 -Uninstall
```

## 使用

- **拖拽**移动；**双击**打开配置；**右键**菜单（配置 / 打卡 / 暂停 / 置顶 / 隐藏 / 退出）
- 托盘：显示窗口、打开配置、退出
- 配置在 `data/config.json`，重启仍在

## 配置项

| 分区 | 内容 |
|------|------|
| 薪资 | 月薪 / 日薪 / 时薪；加班倍率；发薪日 |
| 工时 | 上班/下班、午休；是否扣午休；自动排班计时 |
| 出勤 | 按月日历勾选；一键工作日 / 全选 / 清空；节假日手改 |
| 显示 | 置顶、透明度 |

## 计算规则（简要）

- **时薪**：月薪 ÷ 本月出勤天数 ÷ 每日净工时（可扣午休）
- **今日**：仅出勤日、工时窗口内（或打卡区间）按秒累计；下班后固定；休息日友好提示
- **本月**：已过出勤日全额 + 今日进度；本月预估与发薪倒计时

## 体验打磨

- 深色圆角卡片 + 阴影层、金色「今日已赚」、薄荷绿进度条
- 数字平滑插值跳动（不闪眼）；上班中轻微呼吸色
- 本月迷你进度条、发薪倒计时文案
- 配置页分区 Tab、出勤日历色块勾选、保存成功反馈
- 中文用微软雅黑；休息/午休/下班友好文案

## 依赖

- Python 3.10+（自带 tkinter）
- 可选：`pywin32`（托盘）、`Pillow`


## 打包 exe

```powershell
cd D:\ieswork\salary-punch
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

产物：`dist\SalaryPunch\SalaryPunch.exe`（onedir，较稳）。配置写在 exe 旁 `data\config.json`（不可写则用 `%AppData%\SalaryPunch`）。

也可双击 `start_exe.bat`。
