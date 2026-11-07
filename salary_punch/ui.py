# -*- coding: utf-8 -*-
"""右下角精致薪资悬浮卡片。"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Callable

from .engine import SalaryEngine, Snapshot, format_money
from .fish import VIEW_LABELS, checkpoint_fish, cycle_fish_view, ensure_auto_fish, end_auto_fish_if_needed, format_duration
from .games import mount_game
from .reminders import ReminderScheduler
from .dark_menu import DarkContextMenu

# palette
BG = "#0B0F17"
BG2 = "#121826"
STROKE = "#1E293B"
ACCENT = "#F5C542"
ACCENT2 = "#34D399"
TEXT = "#E8EEF7"
MUTED = "#8B9BB4"
DIM = "#5B6B82"
BAR_BG = "#1A2332"
FISH = "#FB7185"
_TRANS = "#010203"


class FloatingCard:
    W = 308
    H = 272

    def __init__(
        self,
        root: tk.Tk,
        engine: SalaryEngine,
        on_open_config: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
        on_toggle_visible: Callable[[], None] | None = None,
        on_punch_in: Callable[[], None] | None = None,
        on_punch_out: Callable[[], None] | None = None,
        on_toggle_pause: Callable[[], None] | None = None,
        on_toggle_topmost: Callable[[], None] | None = None,
        on_toggle_fish: Callable[[], None] | None = None,
        on_open_game: Callable[[str], None] | None = None,
    ):
        self.root = root
        self.engine = engine
        self.on_open_config = on_open_config
        self.on_quit = on_quit
        self.on_toggle_visible = on_toggle_visible
        self.on_punch_in = on_punch_in
        self.on_punch_out = on_punch_out
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_topmost = on_toggle_topmost
        self.on_toggle_fish = on_toggle_fish
        self.on_open_game = on_open_game

        self._fish_hint_until = 0.0
        self._fish_ckpt_ticks = 0

        self._drag_x = 0
        self._drag_y = 0
        self._dragging = False
        self._tick = 0
        self._display_today = 0.0
        self._target_today = 0.0
        self._anim_job: str | None = None
        self._refresh_job: str | None = None
        self._snap: Snapshot | None = None
        self._hidden = False
        self._reminders = ReminderScheduler()
        self._remind_job = None
        self._remind_clear_job = None

        cfg = engine.store
        alpha = float(cfg.get("alpha") or 0.95)
        topmost = bool(cfg.get("always_on_top", True))

        self.root.title("薪资打卡器")
        self.root.configure(bg=_TRANS)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", topmost)
        try:
            self.root.attributes("-alpha", alpha)
        except tk.TclError:
            pass
        try:
            self.root.wm_attributes("-transparentcolor", _TRANS)
        except tk.TclError:
            self.root.configure(bg=BG)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - self.W - 24
        y = sh - self.H - 64
        self.root.geometry(f"{self.W}x{self.H}+{x}+{y}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            self.root, width=self.W, height=self.H, bg=_TRANS, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.game_host = tk.Frame(self.root, bg=BG, width=self.W, height=self.H)
        self.game_host.pack_propagate(False)
        self._game_view = None
        self._view = "salary"

        # 广告伪装层（鼠标离开时可盖住真界面）
        self._ad_camouflaged = False
        self._ad_leave_job = None
        self.ad_cover = tk.Frame(self.root, bg="#F3F4F6", width=self.W, height=self.H)
        self.ad_cover.pack_propagate(False)
        self._build_ad_cover()
        self.ad_cover.place_forget()

        self._ids: dict[str, int] = {}
        self._build()
        self._build_menu()

        # 拖拽/双击绑 root+canvas；右键只绑 canvas，避免事件冒泡导致 _popup 连开两次把菜单取消
        for w in (self.root, self.canvas):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._end_drag)
            w.bind("<Double-Button-1>", lambda _e: self._open_config())
            w.bind("<Motion>", self._on_activity)
            w.bind("<Key>", self._on_activity)
        self.canvas.bind("<ButtonRelease-3>", self._popup)
        self._menu_busy = False
        # 广告伪装：离开延迟隐藏，移回恢复
        self.root.bind("<Enter>", self._on_card_enter, add="+")
        self.root.bind("<Leave>", self._on_card_leave, add="+")
        self.ad_cover.bind("<Enter>", self._on_card_enter, add="+")
        self.ad_cover.bind("<ButtonRelease-3>", self._popup)
        for w in (self.ad_cover,):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._end_drag)

        self._schedule_refresh()
        self._schedule_anim()
        self._schedule_reminders()

    def _round_rect(self, x1, y1, x2, y2, r=18, **kw):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kw)

    def _build(self) -> None:
        c = self.canvas
        for i, col in enumerate(("#05070C", "#070A10", "#0A0E15")):
            pad = 10 - i * 2
            self._round_rect(pad, pad, self.W - pad + 2, self.H - pad + 2, r=20, fill=col, outline="")

        self._ids["card"] = self._round_rect(8, 6, self.W - 10, self.H - 10, r=18, fill=BG, outline=STROKE)
        self._ids["strip"] = self._round_rect(8, 6, self.W - 10, 42, r=16, fill=BG2, outline="")
        c.create_rectangle(8, 28, self.W - 10, 42, fill=BG2, outline="")

        self._ids["title"] = c.create_text(
            22, 24, text="薪资打卡 · 到手", fill=TEXT, font=("Microsoft YaHei UI", 11, "bold"), anchor="w"
        )
        self._ids["badge"] = c.create_text(
            self.W - 22, 24, text="税后", fill=ACCENT2, font=("Microsoft YaHei UI", 8, "bold"), anchor="e"
        )
        self._ids["status"] = c.create_text(
            22, 46, text="", fill="#A8B8D0", font=("Microsoft YaHei UI", 9), anchor="w", width=self.W - 44
        )
        self._ids["fish_line"] = c.create_text(
            22, 64, text="", fill=FISH, font=("Microsoft YaHei UI", 8, "bold"), anchor="w", width=self.W - 44,
            tags=("fish_line",),
        )
        c.tag_bind("fish_line", "<Button-1>", lambda _e: self.cycle_fish_stats())
        # 空闲提醒条（默认空，弹出时盖在底部）
        self._ids["remind_bg"] = self._round_rect(14, self.H - 46, self.W - 16, self.H - 14, r=10, fill="#1E293B", outline="")
        self._ids["remind_line"] = c.create_text(
            self.W // 2, self.H - 30, text="", fill=ACCENT, font=("Microsoft YaHei UI", 9, "bold"), anchor="center", width=self.W - 36
        )
        c.itemconfigure(self._ids["remind_bg"], state="hidden")
        c.itemconfigure(self._ids["remind_line"], state="hidden")

        self._ids["today_lbl"] = c.create_text(
            22, 86, text="今日到手", fill=MUTED, font=("Microsoft YaHei UI", 9), anchor="w"
        )
        self._ids["today_amt"] = c.create_text(
            22, 114, text="¥0.00", fill=ACCENT, font=("Microsoft YaHei UI", 20, "bold"), anchor="w"
        )
        self._ids["rate"] = c.create_text(
            self.W - 22, 114, text="", fill=DIM, font=("Microsoft YaHei UI", 8), anchor="e"
        )

        self._ids["bar_bg"] = self._round_rect(22, 136, self.W - 22, 146, r=5, fill=BAR_BG, outline="")
        self._ids["bar_fg"] = self._round_rect(22, 136, 22, 146, r=5, fill=ACCENT2, outline="")
        self._ids["bar_pct"] = c.create_text(
            self.W - 22, 156, text="0%", fill=DIM, font=("Microsoft YaHei UI", 8), anchor="e"
        )
        self._ids["bar_hint"] = c.create_text(
            22, 156, text="今日工时进度", fill=DIM, font=("Microsoft YaHei UI", 8), anchor="w"
        )

        c.create_line(22, 172, self.W - 22, 172, fill=STROKE)

        self._ids["month_lbl"] = c.create_text(
            22, 190, text="本周期到手", fill=MUTED, font=("Microsoft YaHei UI", 8), anchor="w"
        )
        self._ids["month_amt"] = c.create_text(
            22, 210, text="¥0.00", fill=TEXT, font=("Microsoft YaHei UI", 12, "bold"), anchor="w"
        )
        self._ids["days"] = c.create_text(
            self.W - 22, 190, text="周期出勤 0 天", fill=MUTED, font=("Microsoft YaHei UI", 8), anchor="e"
        )
        self._ids["est"] = c.create_text(
            self.W - 22, 210, text="周期预估 ¥0", fill=DIM, font=("Microsoft YaHei UI", 8), anchor="e"
        )

        self._ids["payday"] = c.create_text(
            self.W // 2, 248, text="", fill=DIM, font=("Microsoft YaHei UI", 8), anchor="center"
        )
        self._ids["mbar_bg"] = self._round_rect(22, 224, 140, 230, r=3, fill=BAR_BG, outline="")
        self._ids["mbar_fg"] = self._round_rect(22, 224, 22, 230, r=3, fill=ACCENT, outline="")

    def _set_bar(self, key_bg: str, key_fg: str, x1: int, y1: int, x2: int, y2: int, progress: float, r: int = 5):
        progress = max(0.0, min(1.0, progress))
        self.canvas.delete(self._ids[key_fg])
        width = x2 - x1
        fx2 = x1 + max(0, int(width * progress))
        if fx2 <= x1 + 2:
            self._ids[key_fg] = self.canvas.create_rectangle(x1, y1, x1, y2, fill=ACCENT2, outline="")
        else:
            fill = ACCENT2 if key_fg == "bar_fg" else ACCENT
            self._ids[key_fg] = self._round_rect(x1, y1, fx2, y2, r=r, fill=fill, outline="")

    def apply_snapshot(self, snap: Snapshot) -> None:
        self._snap = snap
        self._target_today = snap.today_earned
        self.canvas.itemconfigure(self._ids["status"], text=snap.status_text[:28])

        net = bool(self.engine.store.get("net_pay", True))
        # 摸鱼时长/血赚常驻可见；单击切换 今日/本月/一共
        view = getattr(snap, "fish_view", None) or self.engine.store.get("fish_view") or "today"
        label = VIEW_LABELS.get(view, "今日")
        if view == "month":
            fsec, fearn = snap.fish_month_seconds, snap.fish_month_earned
        elif view == "all":
            fsec, fearn = snap.fish_all_seconds, snap.fish_all_earned
        else:
            fsec, fearn = snap.fish_today_seconds, snap.fish_today_earned
        scope_fish = f"{label}摸鱼 {format_duration(fsec)} · 血赚 {format_money(fearn)}"
        if snap.fish_active:
            self.canvas.itemconfigure(self._ids["badge"], text="摸鱼中", fill=FISH)
            self.canvas.itemconfigure(self._ids["title"], text="薪资打卡 · 摸鱼血赚")
            fl = (
                f"进行中 {format_duration(snap.fish_session_seconds)}"
                f"/{format_money(snap.fish_session_earned)}｜{scope_fish}"
            )
            self.canvas.itemconfigure(self._ids["fish_line"], text=fl[:48], fill=FISH)
        else:
            self.canvas.itemconfigure(self._ids["badge"], text="税后" if net else "税前", fill=ACCENT2)
            self.canvas.itemconfigure(
                self._ids["title"], text="薪资打卡 · 到手" if net else "薪资打卡 · 税前"
            )
            self.canvas.itemconfigure(self._ids["fish_line"], text=scope_fish, fill="#F9A8D4")


        self.canvas.itemconfigure(self._ids["today_lbl"], text="今日到手" if net else "今日已赚")
        self.canvas.itemconfigure(self._ids["month_lbl"], text="本周期到手" if net else "本周期已赚")
        self.canvas.itemconfigure(self._ids["month_amt"], text=format_money(snap.month_earned))
        self.canvas.itemconfigure(
            self._ids["days"], text=f"周期出勤 {snap.days_worked}/{snap.days_planned} 天"
        )
        self.canvas.itemconfigure(
            self._ids["est"], text=f"周期预估 {format_money(snap.month_estimate)}"
        )
        self.canvas.itemconfigure(self._ids["rate"], text=f"{format_money(snap.hourly_rate)}/时")
        pct = int(round(snap.today_progress * 100))
        self.canvas.itemconfigure(self._ids["bar_pct"], text=f"{pct}%")
        self._set_bar("bar_bg", "bar_fg", 22, 136, self.W - 22, 146, snap.today_progress, r=5)
        self._set_bar("mbar_bg", "mbar_fg", 22, 224, 140, 230, snap.month_progress, r=3)

        ps = (snap.period_start or "")[5:].replace("-", "/")
        pe = (snap.period_end or "")[5:].replace("-", "/")
        span = f"{ps}→{pe}" if ps and pe else ""
        if snap.payday_countdown == 0:
            pd = f"今天发薪日 · 下周期 {span}"
        elif snap.payday_countdown == 1:
            pd = f"明天发薪 · 本周期 {span}"
        else:
            pd = f"本周期 {span} · {snap.payday_countdown} 天后发薪"
        self.canvas.itemconfigure(self._ids["payday"], text=pd)

        color = ACCENT if snap.is_workday else MUTED
        if snap.fish_active:
            color = FISH
        elif snap.is_paused:
            color = "#FBBF24"
        self.canvas.itemconfigure(self._ids["today_amt"], fill=color)


    def cycle_fish_stats(self) -> None:
        """单击摸鱼行：今日 → 本月 → 一共。"""
        try:
            cycle_fish_view(self.engine.store)
            self.apply_snapshot(self.engine.snapshot())
        except Exception:
            pass

    def _schedule_refresh(self) -> None:
        try:
            snap = self.engine.snapshot()
            if self.engine.store.get("paused_today") and self._snap:
                snap = Snapshot(**{**snap.__dict__, "today_earned": self._target_today})
            self.apply_snapshot(snap)
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

    def _schedule_anim(self) -> None:
        self._tick += 1
        diff = self._target_today - self._display_today
        if abs(diff) < 0.005:
            self._display_today = self._target_today
        else:
            self._display_today += diff * 0.18
        text = format_money(self._display_today)
        earning = (
            self._snap
            and self._snap.is_workday
            and not self._snap.is_after_work
            and not self._snap.is_paused
            and not self._snap.is_before_work
            and not self._snap.is_on_lunch
        )
        if self._snap and self._snap.fish_active:
            self.canvas.itemconfigure(self._ids["today_amt"], text=text, fill=FISH)
        elif earning:
            pulse = 0.92 + 0.08 * (0.5 + 0.5 * math.sin(self._tick / 18.0))
            fill = ACCENT if pulse > 0.96 else "#E8B830"
            self.canvas.itemconfigure(self._ids["today_amt"], text=text, fill=fill)
        else:
            self.canvas.itemconfigure(self._ids["today_amt"], text=text)
        self._anim_job = self.root.after(50, self._schedule_anim)

    def _start_drag(self, e):
        self._on_activity()
        # 仅在薪资卡片空白处开始拖；进游戏/菜单后会 clear，避免误跟鼠标
        if getattr(self, "_view", "salary") != "salary":
            self._dragging = False
            return
        if getattr(self, "_menu_busy", False) or getattr(self, "_ad_camouflaged", False):
            # 广告卡仍允许拖，菜单打开时不允许
            if getattr(self, "_menu_busy", False):
                self._dragging = False
                return
        self._dragging = True
        self._drag_x = e.x
        self._drag_y = e.y

    def _end_drag(self, _e=None):
        self._dragging = False

    def _clear_drag(self) -> None:
        self._dragging = False

    def _on_drag(self, e):
        if not getattr(self, "_dragging", False):
            return
        if getattr(self, "_view", "salary") != "salary":
            self._dragging = False
            return
        if getattr(self, "_menu_busy", False):
            self._dragging = False
            return
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _build_menu(self) -> None:
        """兼容旧调用：卡片右键使用深色自绘菜单。"""
        self.menu = None
        self.games_menu = None
        self.apps_menu = None

    def _menu_debug(self, msg: str) -> None:
        try:
            import sys
            from datetime import datetime
            from pathlib import Path as _P

            if getattr(sys, "frozen", False):
                root = _P(sys.executable).resolve().parent
            else:
                root = _P(__file__).resolve().parents[1]
            log = root / "data" / "menu_debug.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
            with log.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def _dismiss_context_menu(self) -> None:
        return

    def _menu_run(self, fn) -> None:
        """直接执行（原生菜单已关闭）。"""
        try:
            fn()
        except Exception as ex:
            self._menu_debug(f"menu_run_error {ex!r}")

    def _card_menu_actions(self) -> dict:
        """命令码 -> 可调用。与托盘编号对齐，并扩展卡片专属项。"""
        return {
            2001: self._open_config,
            2002: lambda: self.on_toggle_fish and self.on_toggle_fish(),
            2003: self.cycle_fish_stats,
            2011: lambda: self.show_game("ttt"),
            2012: lambda: self.show_game("gomoku"),
            2013: lambda: self.show_game("shooter"),
            2021: lambda: self.show_game("advice"),
            2022: lambda: self.show_game("muyu"),
            2023: lambda: self.show_game("coin"),
            2024: lambda: self.show_game("dice"),
            2061: lambda: self.show_game("novel"),
            2062: lambda: self.show_game("memo"),
            2064: lambda: self.show_game("video"),
            2065: lambda: self.show_game("market"),
            2063: self.toggle_ad_camouflage,
            2030: self.show_salary,
            2041: lambda: self.on_punch_in and self.on_punch_in(),
            2042: lambda: self.on_punch_out and self.on_punch_out(),
            2043: lambda: self.on_toggle_pause and self.on_toggle_pause(),
            2051: lambda: self.on_toggle_topmost and self.on_toggle_topmost(),
            2052: lambda: self.on_toggle_visible and self.on_toggle_visible(),
            2099: lambda: self.on_quit and self.on_quit(),
        }

    def _dispatch_card_cmd(self, cmd: int) -> None:
        self._menu_debug(f"dispatch cmd={cmd}")
        fn = self._card_menu_actions().get(int(cmd))
        if not fn:
            self._menu_debug(f"unknown cmd={cmd}")
            return
        try:
            fn()
            self._menu_debug(f"dispatch_ok cmd={cmd}")
        except Exception as ex:
            self._menu_debug(f"dispatch_fail cmd={cmd} err={ex!r}")

    def _dark_popup_menu(self, x_root: int, y_root: int) -> None:
        self._clear_drag()
        """深色自绘菜单（卡片同款配色）；叶子项单击一次即关闭并执行。"""
        if getattr(self, "_menu_busy", False):
            self._menu_debug("dark_ignored_busy")
            return
        self._menu_busy = True

        def done():
            self._menu_busy = False

        actions = self._card_menu_actions()

        def run(cmd: int):
            try:
                self._dispatch_card_cmd(cmd)
            finally:
                done()

        # 关闭菜单但不执行时也要清 busy
        menu = DarkContextMenu(self.root, on_debug=self._menu_debug)
        # 包装：先关菜单再派发（DarkContextMenu 内部已 close）
        def act(cmd: int):
            def _fn():
                run(cmd)
            return _fn

        # 若用户点空白关闭，延迟清 busy
        _orig_close = menu.close

        def close_and_free():
            _orig_close()
            # 若未派发命令，释放 busy
            if not menu._invoked:
                self.root.after(50, done)

        menu.close = close_and_free  # type: ignore

        games = [
            ("item", "井字棋", act(2011)),
            ("item", "五子棋", act(2012)),
            ("item", "Q版雷霆战机", act(2013)),
        ]
        apps = [
            ("item", "人生建议书", act(2021)),
            ("item", "敲木鱼", act(2022)),
            ("item", "命运硬币（做/不做）", act(2023)),
            ("item", "决策骰子", act(2024)),
        ]
        office = [
            ("item", "TXT小说阅读", act(2061)),
            ("item", "工作备忘录", act(2062)),
            ("item", "视频播放", act(2064)),
            ("item", "股票基金", act(2065)),
        ]
        ad_on = bool(self.engine.store.get("ad_camouflage", True))
        ad_label = "🛡  广告伪装：开" if ad_on else "🛡  广告伪装：关"
        spec = [
            ("item", "⚙  打开配置", act(2001)),
            ("sep",),
            ("item", "🐟  进入/退出摸鱼", act(2002)),
            ("item", "📊  切换摸鱼统计（今日/本月/一共）", act(2003)),
            ("sep",),
            ("cascade", "🎮  摸鱼小游戏", games),
            ("cascade", "✨  摸鱼小应用", apps),
            ("cascade", "📂  办公工具", office),
            ("item", ad_label, act(2063)),
            ("item", "💰  返回薪资视图", act(2030)),
            ("sep",),
            ("item", "▶  上班打卡", act(2041)),
            ("item", "■  下班打卡", act(2042)),
            ("item", "⏸  今日暂停/恢复计时", act(2043)),
            ("sep",),
            ("item", "📌  切换置顶", act(2051)),
            ("item", "👁  隐藏窗口", act(2052)),
            ("sep",),
            ("item", "✕  退出", act(2099)),
        ]
        try:
            menu.popup(int(x_root), int(y_root), spec)
            self._menu_debug("dark_popup_shown")
        except Exception as ex:
            self._menu_debug(f"dark_popup_fail {ex!r}")
            done()

    def _popup(self, e):
        self._clear_drag()
        self._on_activity()
        self._on_card_enter()
        if getattr(self, "_menu_busy", False):
            self._menu_debug("popup_ignored_busy")
            return "break"
        try:
            self._dark_popup_menu(int(e.x_root), int(e.y_root))
        except Exception as ex:
            self._menu_debug(f"popup_exception {ex!r}")
            self._menu_busy = False
        return "break"

    def _open_config(self):

        if self.on_open_config:
            self.on_open_config()

    def show(self) -> None:
        self._hidden = False
        self.root.deiconify()
        self.root.lift()

    def hide(self) -> None:
        self._hidden = True
        self.root.withdraw()

    def toggle_visible(self) -> None:
        if self._hidden:
            self.show()
        else:
            self.hide()

    def set_topmost(self, value: bool) -> None:
        self.root.attributes("-topmost", value)

    def set_alpha(self, value: float) -> None:
        try:
            self.root.attributes("-alpha", float(value))
        except tk.TclError:
            pass



    def _on_activity(self, _e=None) -> None:
        try:
            self._reminders.poke()
        except Exception:
            pass

    def _schedule_reminders(self) -> None:
        # 仅在薪资视图弹提醒，不打断游戏
        try:
            if getattr(self, "_view", "salary") == "salary":
                text = self._reminders.maybe_pick()
                if text:
                    self._show_reminder(text)
        except Exception:
            pass
        self._remind_job = self.root.after(20000, self._schedule_reminders)

    def _show_reminder(self, text: str) -> None:
        c = self.canvas
        c.itemconfigure(self._ids["remind_bg"], state="normal")
        c.itemconfigure(self._ids["remind_line"], state="normal", text=text)
        if self._remind_clear_job:
            try:
                self.root.after_cancel(self._remind_clear_job)
            except Exception:
                pass
        self._remind_clear_job = self.root.after(10000, self._hide_reminder)

    def _hide_reminder(self) -> None:
        try:
            self.canvas.itemconfigure(self._ids["remind_bg"], state="hidden")
            self.canvas.itemconfigure(self._ids["remind_line"], state="hidden", text="")
        except Exception:
            pass

    def _unmount_game(self) -> None:
        """只卸下游戏内页，不动摸鱼状态。"""
        if self._game_view is not None:
            try:
                if hasattr(self._game_view, "destroy_game"):
                    self._game_view.destroy_game()
                else:
                    self._game_view.destroy()
            except Exception:
                try:
                    self._game_view.destroy()
                except Exception:
                    pass
            self._game_view = None
        try:
            self.game_host.place_forget()
        except Exception:
            pass
        for child in list(self.game_host.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self.canvas.pack(fill="both", expand=True)
        self._view = "salary"

    def _build_ad_cover(self) -> None:
        """伪装广告卡 UI（同卡片尺寸）。"""
        for child in list(self.ad_cover.winfo_children()):
            child.destroy()
        store = self.engine.store
        title = str(store.get("ad_title") or "企业效率套件 · 限时推广")
        sub = str(store.get("ad_subtitle") or "协同办公 · 文档·日程一站提效")
        footer = str(store.get("ad_footer") or "广告")
        head = tk.Frame(self.ad_cover, bg="#2563EB", height=48)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text=title[:22], bg="#2563EB", fg="white",
                 font=("Microsoft YaHei UI", 10, "bold")).pack(side="left", padx=12, pady=12)
        tk.Label(head, text=footer, bg="#1D4ED8", fg="#DBEAFE",
                 font=("Microsoft YaHei UI", 8), padx=8, pady=2).pack(side="right", padx=10)
        body = tk.Frame(self.ad_cover, bg="#F3F4F6")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(body, text=sub, bg="#F3F4F6", fg="#111827",
                 font=("Microsoft YaHei UI", 11, "bold"), wraplength=self.W - 48, justify="left").pack(anchor="w")
        tk.Label(body, text="✓ 团队协作", bg="#F3F4F6", fg="#374151",
                 font=("Microsoft YaHei UI", 9), justify="left").pack(anchor="w", pady=(12, 0))
        tk.Label(body, text="✓ 日程提醒", bg="#F3F4F6", fg="#374151",
                 font=("Microsoft YaHei UI", 9), justify="left").pack(anchor="w")
        tk.Label(body, text="✓ 一键汇报", bg="#F3F4F6", fg="#374151",
                 font=("Microsoft YaHei UI", 9), justify="left").pack(anchor="w")
        cta = tk.Label(body, text="了解详情", bg="#F59E0B", fg="#1F2937",
                       font=("Microsoft YaHei UI", 9, "bold"), padx=14, pady=6)
        cta.pack(anchor="w", pady=(18, 0))
        tk.Label(self.ad_cover, text="移入恢复 · 右键菜单仍可用", bg="#E5E7EB", fg="#6B7280",
                 font=("Microsoft YaHei UI", 8)).pack(fill="x", side="bottom", pady=4)

    def _pointer_inside_card(self) -> bool:
        try:
            x, y = self.root.winfo_pointerxy()
            w = self.root.winfo_containing(x, y)
            if w is None:
                return False
            # 仍在本窗口树内（含广告层、菜单若挂在 root 下）
            cur = w
            while cur is not None:
                if cur == self.root:
                    return True
                cur = getattr(cur, "master", None)
            return False
        except Exception:
            return False

    def _on_card_enter(self, _e=None) -> None:
        if self._ad_leave_job is not None:
            try:
                self.root.after_cancel(self._ad_leave_job)
            except Exception:
                pass
            self._ad_leave_job = None
        self._hide_ad_camouflage()

    def _on_card_leave(self, _e=None) -> None:
        if not bool(self.engine.store.get("ad_camouflage", True)):
            return
        if getattr(self, "_menu_busy", False):
            return
        delay = int(self.engine.store.get("ad_camouflage_delay_ms") or 450)
        delay = max(120, min(2000, delay))
        if self._ad_leave_job is not None:
            try:
                self.root.after_cancel(self._ad_leave_job)
            except Exception:
                pass
        self._ad_leave_job = self.root.after(delay, self._maybe_show_ad_camouflage)

    def _maybe_show_ad_camouflage(self) -> None:
        self._ad_leave_job = None
        if not bool(self.engine.store.get("ad_camouflage", True)):
            return
        if getattr(self, "_menu_busy", False):
            return
        if self._pointer_inside_card():
            return
        self._show_ad_camouflage()

    def _show_ad_camouflage(self) -> None:
        if self._ad_camouflaged:
            return
        try:
            self._build_ad_cover()
            self.ad_cover.place(x=0, y=0, width=self.W, height=self.H)
            self.ad_cover.lift()
            self._ad_camouflaged = True
        except Exception:
            pass

    def _hide_ad_camouflage(self) -> None:
        if not self._ad_camouflaged:
            return
        try:
            self.ad_cover.place_forget()
        except Exception:
            pass
        self._ad_camouflaged = False

    def toggle_ad_camouflage(self) -> None:
        cur = bool(self.engine.store.get("ad_camouflage", True))
        self.engine.store.update(ad_camouflage=not cur)
        if cur:
            # 关掉伪装
            self._hide_ad_camouflage()
        # 开着则等离开再生效


    def show_salary(self) -> None:
        """切回薪资视图；若摸鱼是进游戏自动开的，则结束本次摸鱼。"""
        self._clear_drag()
        leaving_game = getattr(self, "_view", "salary") != "salary"
        self._unmount_game()
        if leaving_game:
            try:
                snap = self.engine.snapshot()
                end_auto_fish_if_needed(self.engine.store, snap.hourly_rate, snap.today_earned)
                self.apply_snapshot(self.engine.snapshot())
            except Exception:
                pass

    def show_game(self, kind: str) -> None:
        """卡片内打开小游戏/小应用，并默认进入摸鱼计时。"""
        self._clear_drag()
        self._unmount_game()
        try:
            snap = self.engine.snapshot()
            ensure_auto_fish(self.engine.store, snap.hourly_rate, snap.today_earned)
        except Exception:
            pass
        self.canvas.pack_forget()
        self.game_host.place(x=0, y=0, width=self.W, height=self.H)
        self._game_view = mount_game(
            self.game_host,
            kind,
            width=self.W,
            height=self.H,
            on_back=self.show_salary,
            data_dir=self.engine.store.path.parent,
        )
        self._game_view.pack(fill="both", expand=True)
        self._view = kind
        try:
            self._game_view.focus_set()
        except Exception:
            pass


    def destroy(self) -> None:
        try:
            snap = self.engine.snapshot()
            checkpoint_fish(self.engine.store, snap.hourly_rate, snap.today_earned)
        except Exception:
            pass
        try:
            self.show_salary()
        except Exception:
            pass
        for job in (self._anim_job, self._refresh_job, self._remind_job, self._remind_clear_job):
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
        try:
            self.root.destroy()
        except Exception:
            pass
