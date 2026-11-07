# -*- coding: utf-8 -*-
"""上班/下班打卡对话框（防误触 + 严格/自定义工时）。"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Any

from .config import ConfigStore, hhmm_to_minutes


BG = "#0F141F"
PANEL = "#151C2A"
CARD = "#1A2332"
STROKE = "#243044"
TEXT = "#E8EEF7"
MUTED = "#8B9BB4"
ACCENT = "#F5C542"
ACCENT2 = "#34D399"
ENTRY_BG = "#0B101A"


def minutes_to_hhmm(m: int) -> str:
    m = int(m) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def compute_planned_end(
    start_hhmm: str,
    net_hours: float,
    lunch_start: str,
    lunch_end: str,
    deduct_lunch: bool,
) -> str:
    start_m = hhmm_to_minutes(start_hhmm)
    need = max(1, int(round(float(net_hours) * 60)))
    ls = hhmm_to_minutes(lunch_start)
    le = hhmm_to_minutes(lunch_end)
    t = start_m
    worked = 0
    guard = 0
    while worked < need and guard < 24 * 60 + 5:
        guard += 1
        if deduct_lunch and ls <= t < le:
            t = le
            continue
        t += 1
        worked += 1
    return minutes_to_hhmm(t)


def _default_net_hours(store: ConfigStore) -> float:
    from .engine import scheduled_minutes

    return max(0.5, scheduled_minutes(store) / 60.0)


def ask_punch_in(master: tk.Misc, store: ConfigStore) -> dict[str, Any] | None:
    cur = store.punch_today()
    now = datetime.now()
    now_s = now.strftime("%H:%M")

    if cur.get("in"):
        if not messagebox.askyesno(
            "重新上班打卡",
            f"今日已在 {cur.get('in')} 打过上班卡。\n"
            f"重新打卡会覆盖原记录（下班卡也会清空），确认？",
            parent=master,
            icon="warning",
        ):
            return None

    result: dict[str, Any] = {}

    win = tk.Toplevel(master)
    win.title("上班打卡")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.transient(master)
    win.grab_set()

    tk.Label(
        win, text="上班打卡", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold")
    ).pack(anchor="w", padx=18, pady=(16, 4))
    tk.Label(
        win,
        text=f"现在 {now_s} · 打卡后计入今日到手",
        bg=BG,
        fg=MUTED,
        font=("Microsoft YaHei UI", 9),
    ).pack(anchor="w", padx=18)

    body = tk.Frame(win, bg=PANEL)
    body.pack(fill="both", expand=True, padx=16, pady=12)

    mode = tk.StringVar(value="strict")
    ws = str(store.get("work_start", "09:00"))
    we = str(store.get("work_end", "18:00"))

    tk.Radiobutton(
        body,
        text=f"严格按配置工时（{ws}–{we}）\n晚到从现在起算；下班按配置，提前下班请点「下班打卡」",
        variable=mode,
        value="strict",
        bg=PANEL,
        fg=TEXT,
        selectcolor=CARD,
        activebackground=PANEL,
        activeforeground=ACCENT,
        justify="left",
        anchor="w",
        font=("Microsoft YaHei UI", 9),
    ).pack(fill="x", padx=10, pady=(10, 6))

    tk.Radiobutton(
        body,
        text="自定义今日工作时长（净工时，仍按配置扣午休）",
        variable=mode,
        value="custom",
        bg=PANEL,
        fg=TEXT,
        selectcolor=CARD,
        activebackground=PANEL,
        activeforeground=ACCENT,
        justify="left",
        anchor="w",
        font=("Microsoft YaHei UI", 9),
    ).pack(fill="x", padx=10, pady=(4, 4))

    row = tk.Frame(body, bg=PANEL)
    row.pack(fill="x", padx=28, pady=(0, 10))
    tk.Label(row, text="今日工作", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(side="left")
    hours_var = tk.StringVar(value=f"{_default_net_hours(store):.1f}")
    tk.Entry(
        row,
        textvariable=hours_var,
        bg=ENTRY_BG,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        width=8,
        font=("Microsoft YaHei UI", 10),
        highlightthickness=1,
        highlightbackground=STROKE,
        highlightcolor=ACCENT,
    ).pack(side="left", padx=8, ipady=3)
    tk.Label(row, text="小时", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(side="left")

    tip = tk.Label(
        body, text="", bg=PANEL, fg=ACCENT2, font=("Microsoft YaHei UI", 8), justify="left", wraplength=360
    )
    tip.pack(anchor="w", padx=12, pady=(0, 8))

    def refresh_tip(*_a: object) -> None:
        if mode.get() != "custom":
            late = max(hhmm_to_minutes(ws), hhmm_to_minutes(now_s))
            tip.configure(
                text=f"严格模式：今日开工按 {minutes_to_hhmm(late)}，结束按配置 {we}；提前走请下班打卡。"
            )
            return
        try:
            h = float(hours_var.get().strip() or "0")
        except ValueError:
            tip.configure(text="请填写有效小时数，例如 8 或 8.5")
            return
        if h <= 0 or h > 16:
            tip.configure(text="工作时长请在 0.5–16 小时之间")
            return
        end = compute_planned_end(
            now_s,
            h,
            str(store.get("lunch_start", "12:00")),
            str(store.get("lunch_end", "13:00")),
            bool(store.get("deduct_lunch", True)),
        )
        tip.configure(text=f"自定义：从 {now_s} 起算约 {h:g} 小时净工时 → 计划结束 {end}")

    mode.trace_add("write", refresh_tip)
    hours_var.trace_add("write", refresh_tip)
    refresh_tip()

    btns = tk.Frame(win, bg=BG)
    btns.pack(fill="x", padx=16, pady=(0, 14))

    def cancel() -> None:
        result.clear()
        win.destroy()

    def confirm() -> None:
        m = mode.get()
        payload: dict[str, Any] = {
            "in": now_s,
            "out": None,
            "mode": m,
            "punched_at": now.isoformat(timespec="seconds"),
        }
        if m == "custom":
            try:
                h = float(hours_var.get().strip() or "0")
            except ValueError:
                messagebox.showerror("格式错误", "工作时长请填数字", parent=win)
                return
            if h < 0.5 or h > 16:
                messagebox.showerror("范围错误", "工作时长请在 0.5–16 小时", parent=win)
                return
            payload["custom_hours"] = h
            payload["planned_end"] = compute_planned_end(
                now_s,
                h,
                str(store.get("lunch_start", "12:00")),
                str(store.get("lunch_end", "13:00")),
                bool(store.get("deduct_lunch", True)),
            )
        else:
            payload["planned_end"] = we
            payload["custom_hours"] = None
        result.update(payload)
        win.destroy()

    tk.Button(btns, text="取消", bg=CARD, fg=TEXT, relief="flat", padx=14, pady=5, cursor="hand2", command=cancel).pack(
        side="right", padx=(8, 0)
    )
    tk.Button(
        btns,
        text="确认打卡",
        bg=ACCENT,
        fg="#1A1400",
        relief="flat",
        font=("Microsoft YaHei UI", 10, "bold"),
        padx=14,
        pady=5,
        cursor="hand2",
        command=confirm,
    ).pack(side="right")

    win.bind("<Escape>", lambda _e: cancel())
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = 420, 340
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    win.wait_window()
    return result or None


def ask_punch_out(master: tk.Misc, store: ConfigStore) -> str | None:
    cur = store.punch_today()
    now = datetime.now()
    now_s = now.strftime("%H:%M")
    now_m = hhmm_to_minutes(now_s)

    if cur.get("out"):
        if not messagebox.askyesno(
            "重新下班打卡",
            f"今日已在 {cur.get('out')} 打过下班卡。\n"
            f"重新打卡会覆盖为 {now_s}，并按新时间结算今日到手，确认？",
            parent=master,
            icon="warning",
        ):
            return None

    planned = cur.get("planned_end") or store.get("work_end", "18:00")
    planned_m = hhmm_to_minutes(str(planned))
    cfg_end = str(store.get("work_end", "18:00"))

    if now_m < planned_m:
        if not messagebox.askyesno(
            "提前下班确认",
            f"现在 {now_s}，计划/配置结束 {planned}（配置下班 {cfg_end}）。\n\n"
            f"提前下班将按 {now_s} 结算今日到手并停止累计。\n"
            f"若是误触请点「否」。确认提前下班？",
            parent=master,
            icon="warning",
        ):
            return None
    else:
        if not messagebox.askyesno(
            "下班打卡",
            f"确认下班打卡为 {now_s}？\n今日到手将按此时结算。",
            parent=master,
        ):
            return None

    return now_s
