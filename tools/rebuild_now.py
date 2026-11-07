# -*- coding: utf-8 -*-
import os, sys, shutil, subprocess, time
from pathlib import Path

root = Path(r"D:/ieswork/salary-punch")
os.chdir(root)
log = root / "_build_log.txt"

def logw(msg: str) -> None:
    print(msg, flush=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

log.write_text("", encoding="utf-8")
logw("begin rebuild")

# Only kill the running app, not this rebuild script (path also contains salary-punch).
subprocess.run(
    ["taskkill", "/F", "/IM", "SalaryPunch.exe"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match 'python|pythonw' -and $_.CommandLine -and "
        "($_.CommandLine -match 'salary-punch\\\\run\\.py|salary-punch/run\\.py') } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", ps],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    for line in out.splitlines():
        pid = line.strip()
        if pid.isdigit() and int(pid) != os.getpid():
            subprocess.run(
                ["taskkill", "/F", "/PID", pid],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logw(f"killed python run.py {pid}")
except Exception as e:
    logw(f"kill soft fail: {e}")
time.sleep(0.6)

dist = root / "dist" / "SalaryPunch"
bak = Path(os.environ.get("TEMP", ".")) / "sp-data-bak"
if bak.exists():
    shutil.rmtree(bak, ignore_errors=True)
if (dist / "data").exists():
    shutil.copytree(dist / "data", bak)
    logw(f"backed up data -> {bak}")
if dist.exists():
    shutil.rmtree(dist, ignore_errors=True)
    logw("removed dist")

r = subprocess.run([sys.executable, "-X", "utf8", str(root / "tools" / "check_tray_menu.py")])
if r.returncode != 0:
    logw("tray check failed")
    raise SystemExit(2)
logw("tray ok")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean", "--windowed",
    "--name", "SalaryPunch",
    "--onedir",
    "--icon", str(root / "assets" / "tray.ico"),
    "--add-data", "assets;assets",
    "--hidden-import", "salary_punch",
    "--hidden-import", "salary_punch.config",
    "--hidden-import", "salary_punch.config_ui",
    "--hidden-import", "salary_punch.engine",
    "--hidden-import", "salary_punch.phrases",
    "--hidden-import", "salary_punch._period",
    "--hidden-import", "salary_punch.games",
    "--hidden-import", "salary_punch.games.ttt",
    "--hidden-import", "salary_punch.games.gomoku",
    "--hidden-import", "salary_punch.games.shooter",
    "--hidden-import", "salary_punch.games.advice",
    "--hidden-import", "salary_punch.games.novel",
    "--hidden-import", "salary_punch.games.memo",
    "--hidden-import", "salary_punch.games.video",
    "--hidden-import", "salary_punch.games.market",
    "--hidden-import", "cv2",
    "--collect-all", "cv2",
    "--hidden-import", "salary_punch.games.muyu",
    "--hidden-import", "salary_punch.games.coin",
    "--hidden-import", "salary_punch.games.dice",
    "--hidden-import", "salary_punch.reminders",
    "--hidden-import", "salary_punch.fish",
    "--hidden-import", "salary_punch.dark_menu",
    "--hidden-import", "salary_punch.ui",
    "--hidden-import", "salary_punch.tray_win",
    "--hidden-import", "salary_punch.punch_ui",
    "--hidden-import", "salary_punch.autostart",
    "--collect-all", "win32com",
    "--collect-all", "pythonwin",
    "run.py",
]
logw("pyinstaller start")
with log.open("a", encoding="utf-8") as f:
    p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
logw(f"pyinstaller exit={p.returncode}")
if p.returncode != 0:
    raise SystemExit(p.returncode)

(dist / "data").mkdir(parents=True, exist_ok=True)
if bak.exists():
    for item in bak.iterdir():
        dest = dist / "data" / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    shutil.rmtree(bak, ignore_errors=True)
    logw("restored data backup")
dist_cfg = dist / "data" / "config.json"
proj_cfg = root / "data" / "config.json"
if not dist_cfg.exists() and proj_cfg.exists():
    shutil.copy2(proj_cfg, dist_cfg)
    logw("seeded dist config from project (fallback only)")

bat = dist / "start_salarypunch.bat"
bat.write_text(
    '@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0SalaryPunch.exe"\r\n',
    encoding="ascii",
)
exe = dist / "SalaryPunch.exe"
logw(f"OK -> {exe} exists={exe.exists()}")
if not exe.exists():
    raise SystemExit(3)
