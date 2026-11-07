# -*- coding: utf-8 -*-
from __future__ import annotations
import re, shutil
from pathlib import Path

ROOT = Path(r"D:\ieswork\salary-punch")
SP = ROOT / "salary_punch"
SRC = Path(r"D:\ieswork\salary-punch\tools\punch-autostart")
# also try beside this script
HERE = Path(__file__).resolve().parent
for cand in (SRC, HERE / "punch-autostart", HERE):
    if (cand / "punch_ui.py").exists() and (cand / "autostart.py").exists():
        SRC = cand
        break

shutil.copy2(SRC / "punch_ui.py", SP / "punch_ui.py")
shutil.copy2(SRC / "autostart.py", SP / "autostart.py")
print("copied modules from", SRC)

# ---- config.py ----
cfg_path = SP / "config.py"
cfg = cfg_path.read_text(encoding="utf-8")
if '"autostart"' not in cfg:
    cfg = cfg.replace(
        '    "auto_schedule": True,\n',
        '    "auto_schedule": True,\n    "autostart": True,\n    "autostart_prompted": False,\n',
    )
if "def replace_punch" not in cfg:
    old = (
        "    def set_punch(self, day: str, clock_in: str | None = None, clock_out: str | None = None) -> None:\n"
        "        punches = self.data.setdefault(\"punches\", {})\n"
        "        cur = dict(punches.get(day) or {})\n"
        "        if clock_in is not None:\n"
        "            cur[\"in\"] = clock_in\n"
        "        if clock_out is not None:\n"
        "            cur[\"out\"] = clock_out\n"
        "        punches[day] = cur\n"
        "        self.save()\n"
    )
    new = (
        "    def set_punch(self, day: str, clock_in: str | None = None, clock_out: str | None = None, **extra) -> None:\n"
        "        punches = self.data.setdefault(\"punches\", {})\n"
        "        cur = dict(punches.get(day) or {})\n"
        "        if clock_in is not None:\n"
        "            cur[\"in\"] = clock_in\n"
        "        if clock_out is not None:\n"
        "            cur[\"out\"] = clock_out\n"
        "        for k, v in extra.items():\n"
        "            if v is None and k in cur:\n"
        "                cur.pop(k, None)\n"
        "            elif v is not None:\n"
        "                cur[k] = v\n"
        "        punches[day] = cur\n"
        "        self.save()\n"
        "\n"
        "    def replace_punch(self, day: str, payload: dict) -> None:\n"
        "        punches = self.data.setdefault(\"punches\", {})\n"
        "        punches[day] = dict(payload or {})\n"
        "        self.save()\n"
    )
    if old not in cfg:
        raise SystemExit("config set_punch block not found")
    cfg = cfg.replace(old, new)
cfg_path.write_text(cfg, encoding="utf-8")
print("config.py ok")

# ---- engine.py ----
eng_path = SP / "engine.py"
eng = eng_path.read_text(encoding="utf-8")
if "# punch-aware window selection" not in eng:
    old = (
        "        sched_sec = scheduled_minutes(cfg) * 60.0\n"
        "        punch = self.store.punch_today()\n"
        "        paused = bool(cfg.get(\"paused_today\")) and cfg.get(\"paused_date\") == today.isoformat()\n"
        "\n"
        "        auto = bool(cfg.get(\"auto_schedule\", True))\n"
        "        clock_in = punch.get(\"in\") if (not auto or punch.get(\"in\")) else None\n"
        "        clock_out = punch.get(\"out\")\n"
        "\n"
        "        # if manual punch mode and no clock-in yet on workday → 0\n"
        "        if not auto and is_workday and not punch.get(\"in\"):\n"
        "            sec = 0.0\n"
        "        elif not is_workday:\n"
        "            sec = 0.0\n"
        "        elif paused:\n"
        "            # freeze: use last computed stored? approximate with current window but UI freezes\n"
        "            sec = worked_seconds_in_window(\n"
        "                now,\n"
        "                cfg.get(\"work_start\", \"09:00\"),\n"
        "                cfg.get(\"work_end\", \"18:00\"),\n"
        "                cfg.get(\"lunch_start\", \"12:00\"),\n"
        "                cfg.get(\"lunch_end\", \"13:00\"),\n"
        "                bool(cfg.get(\"deduct_lunch\", True)),\n"
        "                clock_in,\n"
        "                clock_out,\n"
        "            )\n"
        "        else:\n"
        "            sec = worked_seconds_in_window(\n"
        "                now,\n"
        "                cfg.get(\"work_start\", \"09:00\"),\n"
        "                cfg.get(\"work_end\", \"18:00\"),\n"
        "                cfg.get(\"lunch_start\", \"12:00\"),\n"
        "                cfg.get(\"lunch_end\", \"13:00\"),\n"
        "                bool(cfg.get(\"deduct_lunch\", True)),\n"
        "                clock_in,\n"
        "                clock_out,\n"
        "            )\n"
    )
    new = (
        "        # punch-aware window selection\n"
        "        punch = self.store.punch_today()\n"
        "        paused = bool(cfg.get(\"paused_today\")) and cfg.get(\"paused_date\") == today.isoformat()\n"
        "\n"
        "        auto = bool(cfg.get(\"auto_schedule\", True))\n"
        "        punch_mode = str(punch.get(\"mode\") or \"strict\")\n"
        "        planned_end = punch.get(\"planned_end\")\n"
        "        custom_hours = punch.get(\"custom_hours\")\n"
        "\n"
        "        win_start = str(cfg.get(\"work_start\", \"09:00\"))\n"
        "        win_end = str(cfg.get(\"work_end\", \"18:00\"))\n"
        "        clock_in = punch.get(\"in\") if (not auto or punch.get(\"in\")) else None\n"
        "        clock_out = punch.get(\"out\")\n"
        "\n"
        "        if punch.get(\"in\") and punch_mode == \"custom\":\n"
        "            win_start = str(punch.get(\"in\"))\n"
        "            win_end = str(planned_end or win_end)\n"
        "            clock_in = str(punch.get(\"in\"))\n"
        "            try:\n"
        "                sched_sec = float(custom_hours) * 3600.0 if custom_hours is not None else scheduled_minutes(cfg) * 60.0\n"
        "            except (TypeError, ValueError):\n"
        "                sched_sec = scheduled_minutes(cfg) * 60.0\n"
        "        else:\n"
        "            sched_sec = scheduled_minutes(cfg) * 60.0\n"
        "\n"
        "        if not auto and is_workday and not punch.get(\"in\"):\n"
        "            sec = 0.0\n"
        "        elif not is_workday:\n"
        "            sec = 0.0\n"
        "        else:\n"
        "            sec = worked_seconds_in_window(\n"
        "                now,\n"
        "                win_start,\n"
        "                win_end,\n"
        "                cfg.get(\"lunch_start\", \"12:00\"),\n"
        "                cfg.get(\"lunch_end\", \"13:00\"),\n"
        "                bool(cfg.get(\"deduct_lunch\", True)),\n"
        "                clock_in,\n"
        "                clock_out,\n"
        "            )\n"
    )
    if old not in eng:
        raise SystemExit("engine punch block not found")
    eng = eng.replace(old, new)

    old2 = (
        "        ws = hhmm_to_minutes(cfg.get(\"work_start\", \"09:00\"))\n"
        "        we = hhmm_to_minutes(cfg.get(\"work_end\", \"18:00\"))\n"
        "        ls = hhmm_to_minutes(cfg.get(\"lunch_start\", \"12:00\"))\n"
        "        le = hhmm_to_minutes(cfg.get(\"lunch_end\", \"13:00\"))\n"
        "        now_m = now.hour * 60 + now.minute + now.second / 60.0\n"
        "        is_before = is_workday and now_m < ws\n"
        "        is_after = is_workday and (bool(clock_out) or now_m >= we)\n"
    )
    new2 = (
        "        end_for_status = win_end\n"
        "        if punch.get(\"in\") and punch_mode == \"custom\" and planned_end:\n"
        "            end_for_status = str(planned_end)\n"
        "        if punch.get(\"in\") and punch_mode != \"custom\":\n"
        "            ws = max(hhmm_to_minutes(cfg.get(\"work_start\", \"09:00\")), hhmm_to_minutes(str(punch.get(\"in\"))))\n"
        "        else:\n"
        "            ws = hhmm_to_minutes(win_start if punch.get(\"in\") else cfg.get(\"work_start\", \"09:00\"))\n"
        "        we = hhmm_to_minutes(end_for_status)\n"
        "        ls = hhmm_to_minutes(cfg.get(\"lunch_start\", \"12:00\"))\n"
        "        le = hhmm_to_minutes(cfg.get(\"lunch_end\", \"13:00\"))\n"
        "        now_m = now.hour * 60 + now.minute + now.second / 60.0\n"
        "        is_before = is_workday and now_m < ws\n"
        "        is_after = is_workday and (bool(clock_out) or now_m >= we)\n"
    )
    if old2 not in eng:
        raise SystemExit("engine status block not found")
    eng = eng.replace(old2, new2)
    eng_path.write_text(eng, encoding="utf-8")
    print("engine.py patched")
else:
    print("engine.py already patched")

# ---- config_ui.py ----
cui_path = SP / "config_ui.py"
cui = cui_path.read_text(encoding="utf-8")
if "var_autostart" not in cui:
    old = (
        "        self.var_ad_camouflage = tk.BooleanVar(value=True)\n"
        "        tk.Checkbutton(\n"
        "            body,\n"
        "            text=\"鼠标离开时伪装为广告卡（可配置）\",\n"
        "            variable=self.var_ad_camouflage,\n"
        "            bg=PANEL,\n"
        "            fg=TEXT,\n"
        "            selectcolor=CARD,\n"
        "            activebackground=PANEL,\n"
        "            font=(\"Microsoft YaHei UI\", 9),\n"
        "        ).pack(anchor=\"w\", pady=(6, 0))\n"
    )
    new = old + (
        "        self.var_autostart = tk.BooleanVar(value=True)\n"
        "        tk.Checkbutton(\n"
        "            body,\n"
        "            text=\"开机自启（写入当前用户启动项）\",\n"
        "            variable=self.var_autostart,\n"
        "            bg=PANEL,\n"
        "            fg=TEXT,\n"
        "            selectcolor=CARD,\n"
        "            activebackground=PANEL,\n"
        "            font=(\"Microsoft YaHei UI\", 9),\n"
        "        ).pack(anchor=\"w\", pady=(6, 0))\n"
    )
    if old not in cui:
        raise SystemExit("config_ui ad block not found")
    cui = cui.replace(old, new)

    old = "        self.var_ad_camouflage.set(bool(d.get(\"ad_camouflage\", True)))\n"
    new = old + "        self.var_autostart.set(bool(d.get(\"autostart\", True)))\n"
    if "var_autostart.set" not in cui:
        if old not in cui:
            raise SystemExit("config_ui load ad not found")
        cui = cui.replace(old, new)

    # save block
    old = "            ad_camouflage=bool(self.var_ad_camouflage.get()),\n            alpha=float(self.alpha_var.get()),\n        )\n"
    if old not in cui:
        raise SystemExit("config_ui save ad not found")
    new = (
        "            ad_camouflage=bool(self.var_ad_camouflage.get()),\n"
        "            autostart=bool(self.var_autostart.get()),\n"
        "            autostart_prompted=True,\n"
        "            alpha=float(self.alpha_var.get()),\n"
        "        )\n"
        "        try:\n"
        "            from .autostart import sync as autostart_sync\n"
        "\n"
        "            autostart_sync(bool(self.var_autostart.get()))\n"
        "        except Exception as e:\n"
        "            messagebox.showwarning(\"开机自启\", f\"同步启动项失败：{e}\", parent=self)\n"
    )
    cui = cui.replace(old, new)

    cui = cui.replace(
        "关闭「自动按排班」后，需右键「上班打卡」才会开始累计今日工资。",
        "关闭「自动按排班」后，需右键「上班打卡」才会开始累计。打卡可选「严格按配置」或「自定义今日时长」；二次打卡/提前下班会二次确认。",
    )
    cui_path.write_text(cui, encoding="utf-8")
    print("config_ui.py patched")
else:
    print("config_ui already patched")

# ---- run.py ----
run_path = ROOT / "run.py"
run = run_path.read_text(encoding="utf-8")
if "ask_punch_in" not in run:
    run = run.replace(
        "from salary_punch.fish import checkpoint_fish, settle_fish_on_exit, toggle_fish\n",
        "from salary_punch.fish import checkpoint_fish, settle_fish_on_exit, toggle_fish\n"
        "from salary_punch.punch_ui import ask_punch_in, ask_punch_out\n"
        "from salary_punch import autostart as autostart_mod\n",
    )
    old = (
        "    def punch_in() -> None:\n"
        "        now = datetime.now().strftime(\"%H:%M\")\n"
        "        day = datetime.now().date().isoformat()\n"
        "        punches = store.data.setdefault(\"punches\", {})\n"
        "        punches[day] = {\"in\": now, \"out\": None}\n"
        "        store.save()\n"
        "\n"
        "    def punch_out() -> None:\n"
        "        now = datetime.now().strftime(\"%H:%M\")\n"
        "        day = datetime.now().date().isoformat()\n"
        "        cur = store.punch_today()\n"
        "        if not cur.get(\"in\"):\n"
        "            store.set_punch(day, clock_in=store.get(\"work_start\", \"09:00\"), clock_out=now)\n"
        "        else:\n"
        "            store.set_punch(day, clock_out=now)\n"
    )
    new = (
        "    def punch_in() -> None:\n"
        "        payload = ask_punch_in(root, store)\n"
        "        if not payload:\n"
        "            return\n"
        "        day = datetime.now().date().isoformat()\n"
        "        store.replace_punch(day, payload)\n"
        "        ui = holder.get(\"ui\")\n"
        "        if ui:\n"
        "            try:\n"
        "                ui.apply_snapshot(engine.snapshot())\n"
        "            except Exception:\n"
        "                pass\n"
        "\n"
        "    def punch_out() -> None:\n"
        "        out_s = ask_punch_out(root, store)\n"
        "        if not out_s:\n"
        "            return\n"
        "        day = datetime.now().date().isoformat()\n"
        "        cur = store.punch_today()\n"
        "        if not cur.get(\"in\"):\n"
        "            store.replace_punch(\n"
        "                day,\n"
        "                {\n"
        "                    \"in\": store.get(\"work_start\", \"09:00\"),\n"
        "                    \"out\": out_s,\n"
        "                    \"mode\": \"strict\",\n"
        "                    \"planned_end\": store.get(\"work_end\", \"18:00\"),\n"
        "                },\n"
        "            )\n"
        "        else:\n"
        "            cur = dict(cur)\n"
        "            cur[\"out\"] = out_s\n"
        "            store.replace_punch(day, cur)\n"
        "        ui = holder.get(\"ui\")\n"
        "        if ui:\n"
        "            try:\n"
        "                ui.apply_snapshot(engine.snapshot())\n"
        "            except Exception:\n"
        "                pass\n"
    )
    if old not in run:
        raise SystemExit("run punch block not found")
    run = run.replace(old, new)

    old = (
        "    root.protocol(\"WM_DELETE_WINDOW\", request_quit)\n"
        "    print(f\"[salary-punch] 运行中  config={store.path}\")\n"
        "    print(f\"[salary-punch] 右键悬浮窗可配置 / 打卡 / 退出\")\n"
        "    root.mainloop()\n"
    )
    new = (
        "    root.protocol(\"WM_DELETE_WINDOW\", request_quit)\n"
        "\n"
        "    def setup_autostart() -> None:\n"
        "        from tkinter import messagebox\n"
        "\n"
        "        try:\n"
        "            already = autostart_mod.is_enabled()\n"
        "        except Exception:\n"
        "            already = False\n"
        "        prompted = bool(store.get(\"autostart_prompted\"))\n"
        "        want = bool(store.get(\"autostart\", True))\n"
        "\n"
        "        if not prompted:\n"
        "            if already:\n"
        "                store.update(autostart=True, autostart_prompted=True)\n"
        "                want = True\n"
        "            else:\n"
        "                ok = messagebox.askyesno(\n"
        "                    \"开机自启\",\n"
        "                    \"是否开机自动启动薪资打卡器？\\n\"\n"
        "                    \"写入当前用户启动项，可随时在「配置 → 显示」开关。\",\n"
        "                    parent=root,\n"
        "                )\n"
        "                want = bool(ok)\n"
        "                store.update(autostart=want, autostart_prompted=True)\n"
        "        try:\n"
        "            autostart_mod.sync(want)\n"
        "            print(f\"[salary-punch] 开机自启={'ON' if want else 'OFF'} -> {autostart_mod.current_value()}\")\n"
        "        except Exception as e:\n"
        "            print(f\"[salary-punch] 开机自启同步失败: {e}\", file=sys.stderr)\n"
        "\n"
        "    root.after(600, setup_autostart)\n"
        "\n"
        "    print(f\"[salary-punch] 运行中  config={store.path}\")\n"
        "    print(f\"[salary-punch] 右键悬浮窗可配置 / 打卡 / 退出\")\n"
        "    root.mainloop()\n"
    )
    if old not in run:
        raise SystemExit("run boot block not found")
    run = run.replace(old, new)
    run_path.write_text(run, encoding="utf-8")
    print("run.py patched")
else:
    print("run.py already patched")

# rebuild_now hidden imports
rb = ROOT / "tools" / "rebuild_now.py"
if rb.exists():
    t = rb.read_text(encoding="utf-8")
    if "salary_punch.punch_ui" not in t:
        t = t.replace(
            '"--hidden-import", "salary_punch.tray_win",\n',
            '"--hidden-import", "salary_punch.tray_win",\n'
            '    "--hidden-import", "salary_punch.punch_ui",\n'
            '    "--hidden-import", "salary_punch.autostart",\n',
        )
        rb.write_text(t, encoding="utf-8")
        print("rebuild_now.py patched")

ps1 = ROOT / "build_exe.ps1"
if ps1.exists():
    t = ps1.read_text(encoding="utf-8")
    if "salary_punch.punch_ui" not in t:
        t = t.replace(
            "  --hidden-import salary_punch.tray_win `\n",
            "  --hidden-import salary_punch.tray_win `\n"
            "  --hidden-import salary_punch.punch_ui `\n"
            "  --hidden-import salary_punch.autostart `\n",
        )
        ps1.write_text(t, encoding="utf-8")
        print("build_exe.ps1 patched")

print("ALL OK")
