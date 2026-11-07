# -*- coding: utf-8 -*-
"""精致配置窗口：薪资 / 工时 / 出勤日历 / 显示。"""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from .config import ConfigStore, weekday_dates

BG = "#0F141F"
PANEL = "#151C2A"
CARD = "#1A2332"
STROKE = "#243044"
TEXT = "#E8EEF7"
MUTED = "#8B9BB4"
ACCENT = "#F5C542"
ACCENT2 = "#34D399"
DANGER = "#F87171"
ENTRY_BG = "#0B101A"


class ConfigWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, store: ConfigStore, on_saved: Callable[[], None] | None = None):
        super().__init__(master)
        self.store = store
        self.on_saved = on_saved
        self.title("薪资打卡 · 配置")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.geometry("520x640")
        self._center()

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(14, 8), font=("Microsoft YaHei UI", 10))
        style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", ACCENT)])
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text="配置中心", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        tk.Label(header, text="改完点保存，悬浮窗立刻生效", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(2, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=16, pady=8)

        self.tab_salary = tk.Frame(self.nb, bg=PANEL)
        self.tab_hours = tk.Frame(self.nb, bg=PANEL)
        self.tab_cal = tk.Frame(self.nb, bg=PANEL)
        self.tab_display = tk.Frame(self.nb, bg=PANEL)
        self.nb.add(self.tab_salary, text="  薪资  ")
        self.nb.add(self.tab_hours, text="  工时  ")
        self.nb.add(self.tab_cal, text="  出勤  ")
        self.nb.add(self.tab_display, text="  显示  ")

        self._build_salary()
        self._build_hours()
        self._build_calendar()
        self._build_display()
        self._load_values()

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=20, pady=(4, 16))
        self.feedback = tk.Label(footer, text="", bg=BG, fg=ACCENT2, font=("Microsoft YaHei UI", 9))
        self.feedback.pack(side="left")

        btn_save = tk.Button(
            footer,
            text="保存并生效",
            bg=ACCENT,
            fg="#1A1400",
            activebackground="#E0B030",
            activeforeground="#1A1400",
            relief="flat",
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._save,
        )
        btn_save.pack(side="right")
        btn_cancel = tk.Button(
            footer,
            text="关闭",
            bg=CARD,
            fg=TEXT,
            activebackground=STROKE,
            relief="flat",
            font=("Microsoft YaHei UI", 10),
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy())

    def _center(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 520, 640
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _section(self, parent, title: str) -> tk.Frame:
        wrap = tk.Frame(parent, bg=PANEL)
        wrap.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(wrap, text=title, bg=PANEL, fg=ACCENT, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        body = tk.Frame(parent, bg=PANEL)
        body.pack(fill="x", padx=16, pady=(4, 8))
        return body

    def _labeled_entry(self, parent, label: str, width: int = 16) -> tk.Entry:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9), width=14, anchor="w").pack(side="left")
        e = tk.Entry(
            row,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 10),
            width=width,
            highlightthickness=1,
            highlightbackground=STROKE,
            highlightcolor=ACCENT,
        )
        e.pack(side="left", ipady=4, padx=(4, 0))
        return e

    def _build_salary(self) -> None:
        body = self._section(self.tab_salary, "计薪方式")
        self.salary_mode = tk.StringVar(value="monthly")
        for text, val in (("月薪", "monthly"), ("日薪", "daily"), ("时薪", "hourly")):
            tk.Radiobutton(
                body,
                text=text,
                variable=self.salary_mode,
                value=val,
                bg=PANEL,
                fg=TEXT,
                selectcolor=CARD,
                activebackground=PANEL,
                activeforeground=ACCENT,
                font=("Microsoft YaHei UI", 10),
            ).pack(side="left", padx=(0, 12))

        body2 = self._section(self.tab_salary, "金额（请填税后到手）")
        self.var_net = tk.BooleanVar(value=True)
        tk.Checkbutton(
            body2,
            text="按税后/到手计算（推荐勾选）",
            variable=self.var_net,
            bg=PANEL,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=PANEL,
            activeforeground=ACCENT,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        self.ent_monthly = self._labeled_entry(body2, "税后月薪（元）")
        self.ent_daily = self._labeled_entry(body2, "税后日薪（元）")
        self.ent_hourly = self._labeled_entry(body2, "税后时薪（元）")
        self.ent_ot = self._labeled_entry(body2, "加班倍率")
        self.ent_payday = self._labeled_entry(body2, "发薪日（几号）")
        tk.Label(body2, text="累计按「上一发薪日→下一发薪日」周期统计，不是自然月", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 8), wraplength=400, justify="left").pack(anchor="w", pady=(4,0))

        tip = tk.Label(
            self.tab_salary,
            text="提示：请填税后到手金额。选月薪时，按本月出勤日自动换算日薪/时薪；主界面会标「到手」。",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
            justify="left",
            wraplength=440,
        )
        tip.pack(anchor="w", padx=16, pady=12)

    def _build_hours(self) -> None:
        body = self._section(self.tab_hours, "标准工时（24小时制 HH:MM）")
        self.ent_ws = self._labeled_entry(body, "上班时间")
        self.ent_we = self._labeled_entry(body, "下班时间")
        self.ent_ls = self._labeled_entry(body, "午休开始")
        self.ent_le = self._labeled_entry(body, "午休结束")

        body2 = self._section(self.tab_hours, "规则")
        self.var_lunch = tk.BooleanVar(value=True)
        self.var_auto = tk.BooleanVar(value=True)
        self.var_weekend = tk.BooleanVar(value=False)
        for text, var in (
            ("扣除午休", self.var_lunch),
            ("自动按排班计时（无需打卡）", self.var_auto),
            ("周末默认算上班（生成出勤时）", self.var_weekend),
        ):
            tk.Checkbutton(
                body2,
                text=text,
                variable=var,
                bg=PANEL,
                fg=TEXT,
                selectcolor=CARD,
                activebackground=PANEL,
                activeforeground=ACCENT,
                font=("Microsoft YaHei UI", 9),
                anchor="w",
            ).pack(fill="x", pady=2)

        tip = tk.Label(
            self.tab_hours,
            text="关闭「自动按排班」后，需右键「上班打卡」才会开始累计。打卡可选「严格按配置」或「自定义今日时长」；二次打卡/提前下班会二次确认。",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
            wraplength=440,
            justify="left",
        )
        tip.pack(anchor="w", padx=16, pady=12)

    def _build_calendar(self) -> None:
        head = tk.Frame(self.tab_cal, bg=PANEL)
        head.pack(fill="x", padx=16, pady=(14, 6))
        today = date.today()
        self.cal_year = tk.IntVar(value=today.year)
        self.cal_month = tk.IntVar(value=today.month)

        tk.Button(head, text="‹", command=self._prev_month, bg=CARD, fg=TEXT, relief="flat", width=3, cursor="hand2").pack(side="left")
        self.cal_title = tk.Label(head, text="", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 12, "bold"))
        self.cal_title.pack(side="left", expand=True)
        tk.Button(head, text="›", command=self._next_month, bg=CARD, fg=TEXT, relief="flat", width=3, cursor="hand2").pack(side="right")

        tools = tk.Frame(self.tab_cal, bg=PANEL)
        tools.pack(fill="x", padx=16, pady=4)
        for text, cmd in (
            ("一键工作日", self._fill_weekdays),
            ("全选", self._fill_all),
            ("清空", self._clear_all),
        ):
            tk.Button(
                tools,
                text=text,
                command=cmd,
                bg=CARD,
                fg=TEXT,
                relief="flat",
                font=("Microsoft YaHei UI", 8),
                padx=8,
                pady=3,
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))

        self.cal_grid = tk.Frame(self.tab_cal, bg=PANEL)
        self.cal_grid.pack(padx=16, pady=8)
        self.day_vars: dict[str, tk.BooleanVar] = {}
        self._render_calendar()

        tip = tk.Label(
            self.tab_cal,
            text="点击日期切换上班/休息。节假日、调休直接手点即可。",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        tip.pack(anchor="w", padx=16, pady=8)

    def _build_display(self) -> None:
        body = self._section(self.tab_display, "窗口")
        self.var_topmost = tk.BooleanVar(value=True)
        tk.Checkbutton(
            body,
            text="始终置顶",
            variable=self.var_topmost,
            bg=PANEL,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=PANEL,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w")
        self.var_ad_camouflage = tk.BooleanVar(value=True)
        tk.Checkbutton(
            body,
            text="鼠标离开时伪装为广告卡（可配置）",
            variable=self.var_ad_camouflage,
            bg=PANEL,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=PANEL,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(6, 0))
        self.var_autostart = tk.BooleanVar(value=True)
        tk.Checkbutton(
            body,
            text="开机自启（写入当前用户启动项）",
            variable=self.var_autostart,
            bg=PANEL,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=PANEL,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(6, 0))

        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x", pady=8)
        tk.Label(row, text="透明度", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9), width=14, anchor="w").pack(side="left")
        self.alpha_var = tk.DoubleVar(value=0.95)
        self.alpha_scale = tk.Scale(
            row,
            from_=0.6,
            to=1.0,
            resolution=0.01,
            orient="horizontal",
            variable=self.alpha_var,
            bg=PANEL,
            fg=TEXT,
            highlightthickness=0,
            troughcolor=CARD,
            length=220,
        )
        self.alpha_scale.pack(side="left")

        tip = tk.Label(
            self.tab_display,
            text="双击悬浮窗也可打开本配置。右键菜单可打卡、暂停、隐藏；广告伪装可在此开关。",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
            wraplength=440,
            justify="left",
        )
        tip.pack(anchor="w", padx=16, pady=12)

    # ----- calendar -----
    def _ym(self) -> tuple[int, int]:
        return self.cal_year.get(), self.cal_month.get()

    def _prev_month(self) -> None:
        y, m = self._ym()
        m -= 1
        if m < 1:
            y, m = y - 1, 12
        self.cal_year.set(y)
        self.cal_month.set(m)
        self._render_calendar()

    def _next_month(self) -> None:
        y, m = self._ym()
        m += 1
        if m > 12:
            y, m = y + 1, 1
        self.cal_year.set(y)
        self.cal_month.set(m)
        self._render_calendar()

    def _render_calendar(self) -> None:
        for w in self.cal_grid.winfo_children():
            w.destroy()
        self.day_vars.clear()
        y, m = self._ym()
        self.cal_title.configure(text=f"{y} 年 {m} 月")
        selected = set(self.store.month_attendance(y, m))

        for i, name in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            tk.Label(self.cal_grid, text=name, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 8), width=4).grid(row=0, column=i, pady=4)

        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(y, m)
        today = date.today()
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(self.cal_grid, text="", bg=PANEL, width=4).grid(row=r, column=c)
                    continue
                iso = date(y, m, day).isoformat()
                var = tk.BooleanVar(value=iso in selected)
                self.day_vars[iso] = var
                is_today = y == today.year and m == today.month and day == today.day
                btn = tk.Checkbutton(
                    self.cal_grid,
                    text=str(day),
                    variable=var,
                    indicatoron=False,
                    width=3,
                    bg=ACCENT2 if var.get() else CARD,
                    fg="#062016" if var.get() else TEXT,
                    selectcolor=ACCENT2,
                    activebackground=ACCENT,
                    relief="flat",
                    font=("Microsoft YaHei UI", 9, "bold" if is_today else "normal"),
                    cursor="hand2",
                    command=lambda i=iso: self._on_day_toggle(i),
                )
                btn.grid(row=r, column=c, padx=2, pady=2, ipady=4)
                setattr(self, f"_btn_{iso}", btn)
        self._sync_day_colors()

    def _on_day_toggle(self, iso: str) -> None:
        self._sync_day_colors()

    def _sync_day_colors(self) -> None:
        for iso, var in self.day_vars.items():
            btn = getattr(self, f"_btn_{iso}", None)
            if not btn:
                continue
            if var.get():
                btn.configure(bg=ACCENT2, fg="#062016")
            else:
                btn.configure(bg=CARD, fg=TEXT)

    def _fill_weekdays(self) -> None:
        y, m = self._ym()
        days = set(weekday_dates(y, m, include_weekend=False))
        for iso, var in self.day_vars.items():
            var.set(iso in days)
        self._sync_day_colors()

    def _fill_all(self) -> None:
        for var in self.day_vars.values():
            var.set(True)
        self._sync_day_colors()

    def _clear_all(self) -> None:
        for var in self.day_vars.values():
            var.set(False)
        self._sync_day_colors()

    # ----- load / save -----
    def _load_values(self) -> None:
        d = self.store.data
        self.salary_mode.set(d.get("salary_mode", "monthly"))
        self.var_net.set(bool(d.get("net_pay", True)))
        self.ent_monthly.insert(0, str(d.get("monthly_salary", 15000)))
        self.ent_daily.insert(0, str(d.get("daily_salary", 0)))
        self.ent_hourly.insert(0, str(d.get("hourly_salary", 0)))
        self.ent_ot.insert(0, str(d.get("overtime_rate", 1.5)))
        self.ent_payday.insert(0, str(d.get("payday", 10)))
        self.ent_ws.insert(0, str(d.get("work_start", "09:00")))
        self.ent_we.insert(0, str(d.get("work_end", "18:00")))
        self.ent_ls.insert(0, str(d.get("lunch_start", "12:00")))
        self.ent_le.insert(0, str(d.get("lunch_end", "13:00")))
        self.var_lunch.set(bool(d.get("deduct_lunch", True)))
        self.var_auto.set(bool(d.get("auto_schedule", True)))
        self.var_weekend.set(bool(d.get("weekend_is_workday", False)))
        self.var_topmost.set(bool(d.get("always_on_top", True)))
        self.var_ad_camouflage.set(bool(d.get("ad_camouflage", True)))
        self.var_autostart.set(bool(d.get("autostart", True)))
        self.alpha_var.set(float(d.get("alpha", 0.95)))

    def _f(self, entry: tk.Entry, default: float = 0.0) -> float:
        try:
            return float(str(entry.get()).strip().replace(",", "") or default)
        except ValueError:
            return default

    def _save(self) -> None:
        try:
            payday = int(float(self.ent_payday.get().strip() or "10"))
            payday = max(1, min(28, payday))
        except ValueError:
            messagebox.showerror("格式错误", "发薪日请填 1–28 的数字", parent=self)
            return

        for label, ent in (("上班", self.ent_ws), ("下班", self.ent_we), ("午休开始", self.ent_ls), ("午休结束", self.ent_le)):
            val = ent.get().strip()
            if len(val.split(":")) != 2:
                messagebox.showerror("格式错误", f"{label}时间请用 HH:MM", parent=self)
                return

        y, m = self._ym()
        days = [iso for iso, var in self.day_vars.items() if var.get()]
        self.store.set_month_attendance(y, m, days)

        self.store.update(
            salary_mode=self.salary_mode.get(),
            net_pay=bool(self.var_net.get()),
            monthly_salary=self._f(self.ent_monthly, 15000),
            daily_salary=self._f(self.ent_daily, 0),
            hourly_salary=self._f(self.ent_hourly, 0),
            overtime_rate=self._f(self.ent_ot, 1.5) or 1.5,
            payday=payday,
            work_start=self.ent_ws.get().strip(),
            work_end=self.ent_we.get().strip(),
            lunch_start=self.ent_ls.get().strip(),
            lunch_end=self.ent_le.get().strip(),
            deduct_lunch=self.var_lunch.get(),
            auto_schedule=self.var_auto.get(),
            weekend_is_workday=self.var_weekend.get(),
            always_on_top=self.var_topmost.get(),
            ad_camouflage=bool(self.var_ad_camouflage.get()),
            autostart=bool(self.var_autostart.get()),
            autostart_prompted=True,
            alpha=float(self.alpha_var.get()),
        )
        try:
            from .autostart import sync as autostart_sync

            autostart_sync(bool(self.var_autostart.get()))
        except Exception as e:
            messagebox.showwarning("开机自启", f"同步启动项失败：{e}", parent=self)
        self.feedback.configure(text="✓ 已保存，悬浮窗已更新")
        if self.on_saved:
            self.on_saved()
        self.after(1800, lambda: self.feedback.configure(text=""))
