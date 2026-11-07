# -*- coding: utf-8 -*-
"""Fix fish stats persistence: AppData canonical store + checkpoint + rebuild-safe."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(r"D:\ieswork\salary-punch")

RUN_PY_NEW = r'''# -*- coding: utf-8 -*-
"""薪资打卡器 — 入口。"""

from __future__ import annotations

import json
import shutil
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path


def app_root() -> Path:
    """源码目录，或 PyInstaller 解压/可执行文件旁。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _cfg_fish_score(path: Path) -> float:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return -1.0
        return float(raw.get("fish_seconds_all") or 0) + float(
            raw.get("fish_seconds_today") or 0
        )
    except Exception:
        return -1.0


def _migrate_tree(src: Path, dst: Path) -> None:
    """把旧 data 目录里的文件补进目标（不覆盖已有非空 config 的更高累计）。"""
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            if not target.exists():
                shutil.copytree(item, target)
            else:
                _migrate_tree(item, target)
            continue
        if item.name == "config.json":
            if not target.exists():
                shutil.copy2(item, target)
            elif _cfg_fish_score(item) > _cfg_fish_score(target):
                # 旧位置累计更大：合并覆盖（保留更大摸鱼数）
                shutil.copy2(item, target)
            continue
        if not target.exists():
            try:
                shutil.copy2(item, target)
            except OSError:
                pass


def data_dir_path(root: Path) -> Path:
    """摸鱼/配置持久化固定在 AppData，避免每次重打包删掉 dist 数据。

    启动时从旧位置（项目 data / exe 旁 data）迁移一次。
    """
    appdata = Path.home() / "AppData" / "Roaming" / "SalaryPunch"
    appdata.mkdir(parents=True, exist_ok=True)

    candidates = [
        root / "data",
        Path(__file__).resolve().parent / "data",
        root.parent.parent / "data" if root.name.lower() == "salarypunch" else None,
    ]
    # frozen: root=.../dist/SalaryPunch → 项目 data 在 ../../data
    try:
        proj = Path(__file__).resolve().parent
        candidates.append(proj / "data")
        candidates.append(proj / "dist" / "SalaryPunch" / "data")
    except Exception:
        pass

    seen: set[str] = set()
    for c in candidates:
        if c is None:
            continue
        key = str(c.resolve()) if c.exists() else str(c)
        if key in seen:
            continue
        seen.add(key)
        if c.exists() and c.resolve() != appdata.resolve():
            _migrate_tree(c, appdata)

    return appdata


ROOT = app_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# frozen: modules live in _MEIPASS
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    meipass = str(sys._MEIPASS)
    if meipass not in sys.path:
        sys.path.insert(0, meipass)

from salary_punch.config import ConfigStore
from salary_punch.config_ui import ConfigWindow
from salary_punch.engine import SalaryEngine
from salary_punch.ui import FloatingCard
from salary_punch.fish import checkpoint_fish, settle_fish_on_exit, toggle_fish


def main() -> int:
    data_dir = data_dir_path(ROOT)
    data_dir.mkdir(parents=True, exist_ok=True)
    store = ConfigStore(data_dir / "config.json")
    engine = SalaryEngine(store)

    root = tk.Tk()
    root.withdraw()

    holder: dict = {"ui": None, "tray": None, "cfg": None}

    def request_quit() -> None:
        root.after(0, shutdown)

    def open_config() -> None:
        existing = holder.get("cfg")
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                pass

        def on_saved() -> None:
            ui = holder["ui"]
            if ui:
                ui.set_topmost(bool(store.get("always_on_top", True)))
                ui.set_alpha(float(store.get("alpha") or 0.95))
                # force refresh next tick
                try:
                    ui.apply_snapshot(engine.snapshot())
                except Exception:
                    pass

        win = ConfigWindow(root, store, on_saved=on_saved)
        holder["cfg"] = win

    def punch_in() -> None:
        now = datetime.now().strftime("%H:%M")
        day = datetime.now().date().isoformat()
        punches = store.data.setdefault("punches", {})
        punches[day] = {"in": now, "out": None}
        store.save()

    def punch_out() -> None:
        now = datetime.now().strftime("%H:%M")
        day = datetime.now().date().isoformat()
        cur = store.punch_today()
        if not cur.get("in"):
            store.set_punch(day, clock_in=store.get("work_start", "09:00"), clock_out=now)
        else:
            store.set_punch(day, clock_out=now)

    def toggle_pause() -> None:
        today = datetime.now().date().isoformat()
        paused = bool(store.get("paused_today")) and store.get("paused_date") == today
        store.update(paused_today=not paused, paused_date=today)

    def toggle_topmost() -> None:
        cur = bool(store.get("always_on_top", True))
        store.update(always_on_top=not cur)
        ui = holder["ui"]
        if ui:
            ui.set_topmost(not cur)

    def on_toggle_visible() -> None:
        ui = holder["ui"]
        if ui:
            ui.toggle_visible()


    def do_toggle_fish() -> None:
        snap = engine.snapshot()
        active = toggle_fish(store, snap.hourly_rate, snap.today_earned)
        ui = holder.get("ui")
        if ui:
            try:
                ui.apply_snapshot(engine.snapshot())
            except Exception:
                pass
        print(f"[salary-punch] 摸鱼={'ON' if active else 'OFF'}")

    def do_open_game(kind: str) -> None:
        u = holder.get("ui")
        if u:
            u.show_game(kind)

    ui = FloatingCard(

        root,
        engine,
        on_open_config=lambda: root.after(0, open_config),
        on_quit=request_quit,
        on_toggle_visible=on_toggle_visible,
        on_punch_in=lambda: root.after(0, punch_in),
        on_punch_out=lambda: root.after(0, punch_out),
        on_toggle_pause=lambda: root.after(0, toggle_pause),
        on_toggle_topmost=lambda: root.after(0, toggle_topmost),
        on_toggle_fish=lambda: root.after(0, do_toggle_fish),
        on_open_game=lambda k: root.after(0, lambda kk=k: do_open_game(kk)),
    )
    holder["ui"] = ui
    root.deiconify()
    ui.show()

    try:
        from salary_punch.tray_win import TrayApp

        tray = TrayApp(
            icon_path=(Path(getattr(sys, "_MEIPASS", ROOT)) / "assets" / "tray.ico"),
            on_show=lambda: root.after(0, ui.show),
            on_config=lambda: root.after(0, open_config),
            on_quit=request_quit,
            on_toggle_fish=lambda: root.after(0, do_toggle_fish),
            on_open_game=lambda k: root.after(0, lambda kk=k: do_open_game(kk)),
            on_cycle_fish_stats=lambda: root.after(0, ui.cycle_fish_stats),
            on_show_salary=lambda: root.after(0, ui.show_salary),
            on_punch_in=lambda: root.after(0, punch_in),
            on_punch_out=lambda: root.after(0, punch_out),
            on_toggle_pause=lambda: root.after(0, toggle_pause),
            on_toggle_topmost=lambda: root.after(0, toggle_topmost),
            on_toggle_visible=lambda: root.after(0, on_toggle_visible),
            on_toggle_ad_camouflage=lambda: root.after(0, ui.toggle_ad_camouflage),
            tooltip="薪资打卡器",
        )
        tray.start()
        holder["tray"] = tray
    except Exception as e:
        print(f"[salary-punch] 托盘不可用: {e}", file=sys.stderr)

    def shutdown() -> None:
        # 退出前把进行中的摸鱼结算进今日/本月/一共，避免杀进程丢时长
        try:
            snap = engine.snapshot()
            settle_fish_on_exit(store, snap.hourly_rate, snap.today_earned)
        except Exception:
            try:
                settle_fish_on_exit(store, 0.0, 0.0)
            except Exception:
                pass
        tray = holder.get("tray")
        if tray:
            try:
                tray.stop()
            except Exception:
                pass
        try:
            ui.destroy()
        except Exception:
            pass
        try:
            root.quit()
            root.destroy()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", request_quit)
    print(f"[salary-punch] 运行中  config={store.path}")
    print(f"[salary-punch] 右键悬浮窗可配置 / 打卡 / 退出")
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

FISH_APPEND_FUNCS = r'''

def checkpoint_fish(store: ConfigStore, hourly_rate: float, today_earned: float) -> None:
    """进行中会话定期落盘：把 live 秒数并入今日/本月/一共，并重置本段起点。

    杀进程也能保住大部分时长；界面上的「进行中」会从 0 再累加。
    """
    clear_fish_if_new_day(store, hourly_rate, today_earned)
    if not store.get("fishing"):
        return
    live_sec, live_earn = _compute_live(store, hourly_rate, today_earned)
    if live_sec <= 0 and live_earn <= 0:
        return
    store.update(
        fish_seconds_today=float(store.get("fish_seconds_today") or 0) + live_sec,
        fish_earned_today=float(store.get("fish_earned_today") or 0) + live_earn,
        fish_seconds_month=float(store.get("fish_seconds_month") or 0) + live_sec,
        fish_earned_month=float(store.get("fish_earned_month") or 0) + live_earn,
        fish_seconds_all=float(store.get("fish_seconds_all") or 0) + live_sec,
        fish_earned_all=float(store.get("fish_earned_all") or 0) + live_earn,
        fish_started_at=now_local().isoformat(timespec="seconds"),
        fish_session_base_earned=float(today_earned),
        fish_day=date.today().isoformat(),
        fish_month=_month_key(),
    )


def settle_fish_on_exit(store: ConfigStore, hourly_rate: float, today_earned: float) -> None:
    """退出进程：无论手动/自动摸鱼都结算并关闭会话。"""
    if store.get("fishing"):
        stop_fish(store, hourly_rate, today_earned)
    else:
        # 确保已写盘
        try:
            store.save()
        except Exception:
            pass
'''


def patch_fish(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "def checkpoint_fish" in text:
        print("fish.py already has checkpoint_fish")
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + FISH_APPEND_FUNCS, encoding="utf-8")
    print("patched fish.py")


def patch_ui(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old_import = "from .fish import VIEW_LABELS, cycle_fish_view, ensure_auto_fish, end_auto_fish_if_needed, format_duration"
    new_import = "from .fish import VIEW_LABELS, checkpoint_fish, cycle_fish_view, ensure_auto_fish, end_auto_fish_if_needed, format_duration"
    if "checkpoint_fish" not in text:
        if old_import not in text:
            raise SystemExit("ui.py import line not found")
        text = text.replace(old_import, new_import, 1)

    # add checkpoint counter in __init__ near _fish_hint_until
    if "self._fish_ckpt_ticks" not in text:
        needle = "        self._fish_hint_until = 0.0\n"
        if needle not in text:
            raise SystemExit("ui.py _fish_hint_until not found")
        text = text.replace(
            needle,
            needle + "        self._fish_ckpt_ticks = 0\n",
            1,
        )

    # in _schedule_refresh, checkpoint every 15 seconds while fishing
    marker = "            self.apply_snapshot(snap)\n        except Exception as e:\n            self.canvas.itemconfigure(self._ids[\"status\"], text=f\"错误: {e}\"[:20])\n        self._refresh_job = self.root.after(1000, self._schedule_refresh)\n"
    if "checkpoint_fish(" not in text:
        insert = '''            self.apply_snapshot(snap)
            # 摸鱼进行中每 15 秒落盘，防止杀进程/重打包丢时长
            self._fish_ckpt_ticks = getattr(self, "_fish_ckpt_ticks", 0) + 1
            if snap.fish_active and self._fish_ckpt_ticks % 15 == 0:
                try:
                    checkpoint_fish(
                        self.engine.store, snap.hourly_rate, snap.today_earned
                    )
                except Exception:
                    pass
        except Exception as e:
            self.canvas.itemconfigure(self._ids["status"], text=f"错误: {e}"[:20])
        self._refresh_job = self.root.after(1000, self._schedule_refresh)
'''
        if marker not in text:
            raise SystemExit("ui.py refresh marker not found")
        text = text.replace(marker, insert, 1)

    # destroy: settle before unmount
    if "settle_fish_on_exit" not in text and "checkpoint_fish" in text:
        # soft: call checkpoint in destroy before show_salary
        old_destroy = '''    def destroy(self) -> None:
        try:
            self.show_salary()
        except Exception:
            pass
'''
        new_destroy = '''    def destroy(self) -> None:
        try:
            snap = self.engine.snapshot()
            checkpoint_fish(self.engine.store, snap.hourly_rate, snap.today_earned)
        except Exception:
            pass
        try:
            self.show_salary()
        except Exception:
            pass
'''
        if old_destroy not in text:
            print("WARN: destroy block not exact; skip destroy patch")
        else:
            text = text.replace(old_destroy, new_destroy, 1)

    path.write_text(text, encoding="utf-8")
    print("patched ui.py")


def patch_build(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    # Replace wipe+copy section to preserve data
    old = '''$dist = Join-Path $PSScriptRoot 'dist\\SalaryPunch'
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }

# 先停掉正在跑的，避免占用
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match 'salary-punch|SalaryPunch') } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
'''
    new = '''$dist = Join-Path $PSScriptRoot 'dist\\SalaryPunch'

# 先停掉正在跑的，避免占用；并尽量让摸鱼时长已落在 AppData
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match 'salary-punch|SalaryPunch') } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 400

# 重打包前备份 dist 旁 data（摸鱼统计已迁 AppData，这里只保小说/视频等旁路文件）
$dataBackup = Join-Path $env:TEMP ("SalaryPunch-data-bak-" + [guid]::NewGuid().ToString("N"))
if (Test-Path (Join-Path $dist 'data')) {
  Copy-Item (Join-Path $dist 'data') $dataBackup -Recurse -Force
}
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
'''
    if "SalaryPunch-data-bak" not in text:
        if old not in text:
            # try softer match
            if "Remove-Item -Recurse -Force $dist" not in text:
                raise SystemExit("build_exe.ps1 wipe not found")
            print("WARN: exact wipe block mismatch, doing partial")
        else:
            text = text.replace(old, new, 1)

    old_copy = '''# 旁路可写 data（从现有配置拷一份）
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'data') | Out-Null
$cfg = Join-Path $PSScriptRoot 'data\\config.json'
if (Test-Path $cfg) {
  Copy-Item $cfg (Join-Path $dist 'data\\config.json') -Force
}
'''
    new_copy = '''# 旁路可写 data：恢复备份；配置以 AppData\\SalaryPunch 为准，这里不覆盖摸鱼累计
New-Item -ItemType Directory -Force -Path (Join-Path $dist 'data') | Out-Null
if (Test-Path $dataBackup) {
  Copy-Item (Join-Path $dataBackup '*') (Join-Path $dist 'data') -Recurse -Force
  Remove-Item $dataBackup -Recurse -Force -ErrorAction SilentlyContinue
}
# 仅当 dist data 没有 config 时，从项目 data 拷一份「非摸鱼」默认（仍会被 AppData 迁移逻辑盖过）
$distCfg = Join-Path $dist 'data\\config.json'
$cfg = Join-Path $PSScriptRoot 'data\\config.json'
if (-not (Test-Path $distCfg) -and (Test-Path $cfg)) {
  Copy-Item $cfg $distCfg -Force
}
'''
    if "配置以 AppData" not in text:
        if old_copy not in text:
            raise SystemExit("build copy block not found")
        text = text.replace(old_copy, new_copy, 1)

    path.write_text(text, encoding="utf-8")
    print("patched build_exe.ps1")


def merge_best_config_into_appdata() -> None:
    """One-shot: pick the config with highest fish_seconds_all into AppData."""
    appdata = Path.home() / "AppData" / "Roaming" / "SalaryPunch"
    appdata.mkdir(parents=True, exist_ok=True)
    candidates = [
        ROOT / "data" / "config.json",
        ROOT / "dist" / "SalaryPunch" / "data" / "config.json",
        appdata / "config.json",
    ]
    best = None
    best_score = -1.0
    for c in candidates:
        if not c.exists():
            continue
        try:
            raw = json.loads(c.read_text(encoding="utf-8"))
            score = float(raw.get("fish_seconds_all") or 0) + float(
                raw.get("fish_seconds_today") or 0
            )
        except Exception:
            continue
        print(f" candidate {c} score={score}")
        if score > best_score:
            best_score = score
            best = c
    if best is None:
        print("no config found to seed")
        return
    dest = appdata / "config.json"
    if best.resolve() != dest.resolve():
        shutil.copy2(best, dest)
        print(f"seeded AppData from {best} (score={best_score})")
    else:
        print(f"AppData already best score={best_score}")
    # also migrate media folders
    for src_root in [ROOT / "data", ROOT / "dist" / "SalaryPunch" / "data"]:
        if not src_root.is_dir():
            continue
        for name in ("novels", "videos", "work_memo.txt", "video_state.json"):
            s = src_root / name
            d = appdata / name
            if not s.exists() or d.exists():
                continue
            if s.is_dir():
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
            print(f"migrated {s} -> {d}")


def main() -> None:
    patch_fish(ROOT / "salary_punch" / "fish.py")
    patch_ui(ROOT / "salary_punch" / "ui.py")
    (ROOT / "run.py").write_text(RUN_PY_NEW, encoding="utf-8")
    print("wrote run.py")
    patch_build(ROOT / "build_exe.ps1")
    merge_best_config_into_appdata()
    print("DONE")


if __name__ == "__main__":
    main()
