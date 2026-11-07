# -*- coding: utf-8 -*-
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
from salary_punch.punch_ui import ask_punch_in, ask_punch_out
from salary_punch import autostart as autostart_mod


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
        payload = ask_punch_in(root, store)
        if not payload:
            return
        day = datetime.now().date().isoformat()
        store.replace_punch(day, payload)
        ui = holder.get("ui")
        if ui:
            try:
                ui.apply_snapshot(engine.snapshot())
            except Exception:
                pass

    def punch_out() -> None:
        out_s = ask_punch_out(root, store)
        if not out_s:
            return
        day = datetime.now().date().isoformat()
        cur = store.punch_today()
        if not cur.get("in"):
            store.replace_punch(
                day,
                {
                    "in": store.get("work_start", "09:00"),
                    "out": out_s,
                    "mode": "strict",
                    "planned_end": store.get("work_end", "18:00"),
                },
            )
        else:
            cur = dict(cur)
            cur["out"] = out_s
            store.replace_punch(day, cur)
        ui = holder.get("ui")
        if ui:
            try:
                ui.apply_snapshot(engine.snapshot())
            except Exception:
                pass

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

    def setup_autostart() -> None:
        from tkinter import messagebox

        try:
            already = autostart_mod.is_enabled()
        except Exception:
            already = False
        prompted = bool(store.get("autostart_prompted"))
        want = bool(store.get("autostart", True))

        if not prompted:
            if already:
                store.update(autostart=True, autostart_prompted=True)
                want = True
            else:
                ok = messagebox.askyesno(
                    "开机自启",
                    "是否开机自动启动薪资打卡器？\n"
                    "写入当前用户启动项，可随时在「配置 → 显示」开关。",
                    parent=root,
                )
                want = bool(ok)
                store.update(autostart=want, autostart_prompted=True)
        try:
            autostart_mod.sync(want)
            print(f"[salary-punch] 开机自启={'ON' if want else 'OFF'} -> {autostart_mod.current_value()}")
        except Exception as e:
            print(f"[salary-punch] 开机自启同步失败: {e}", file=sys.stderr)

    root.after(600, setup_autostart)

    print(f"[salary-punch] 运行中  config={store.path}")
    print(f"[salary-punch] 右键悬浮窗可配置 / 打卡 / 退出")
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
