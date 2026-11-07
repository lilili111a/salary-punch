# -*- coding: utf-8 -*-
"""与薪资卡片统一的深色自绘右键菜单；叶子项单击一次即回调并关闭。"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

BG2 = "#121826"
STROKE = "#1E293B"
ACCENT = "#F5C542"
TEXT = "#E8EEF7"
ACTIVE = "#1E293B"
ROW_H = 32
PAD_X = 14
MIN_W = 208
# 子菜单与父项重叠，避免鼠标穿越空隙时 Leave 关掉子菜单
SUB_OVERLAP = 8


class DarkContextMenu:
    """自绘深色菜单。级联用独立 Toplevel，不用 grab 以免挡住子菜单点击。"""

    _outside_armed: DarkContextMenu | None = None
    _outside_handler_bound = False

    @classmethod
    def _ensure_outside_handler(cls, master: tk.Misc) -> None:
        if cls._outside_handler_bound:
            return

        def on_global_press(e) -> None:
            armed = cls._outside_armed
            if armed is None or armed._closed or armed._invoked:
                return
            if armed._point_in_menus(e.x_root, e.y_root, inflate=1):
                return
            armed.close()

        try:
            master.bind_all("<ButtonPress-1>", on_global_press, add="+")
            cls._outside_handler_bound = True
        except Exception:
            pass

    def __init__(self, master: tk.Misc, on_debug: Callable[[str], None] | None = None):
        self.master = master
        self.on_debug = on_debug or (lambda _m: None)
        self._wins: list[tk.Toplevel] = []
        self._closed = False
        self._invoked = False
        self._active_sub: tk.Toplevel | None = None
        self._sub_close_job: str | None = None
        self._outside_job: str | None = None
        # panel(inner Frame) -> currently highlighted row
        self._hover_row: dict[int, tk.Frame] = {}

    def _log(self, msg: str) -> None:
        try:
            self.on_debug(msg)
        except Exception:
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._cancel_sub_close()
        if DarkContextMenu._outside_armed is self:
            DarkContextMenu._outside_armed = None
        if self._outside_job:
            try:
                self.master.after_cancel(self._outside_job)
            except Exception:
                pass
            self._outside_job = None
        for w in list(self._wins):
            try:
                w.destroy()
            except Exception:
                pass
        self._wins.clear()
        self._active_sub = None
        self._hover_row.clear()

    def _cancel_sub_close(self) -> None:
        if self._sub_close_job:
            try:
                self.master.after_cancel(self._sub_close_job)
            except Exception:
                pass
            self._sub_close_job = None

    def _point_in_menus(self, x_root: int, y_root: int, *, inflate: int = 0) -> bool:
        for w in self._wins:
            try:
                if not w.winfo_exists():
                    continue
                wx, wy = w.winfo_rootx(), w.winfo_rooty()
                ww, wh = w.winfo_width(), w.winfo_height()
                if (
                    wx - inflate <= x_root <= wx + ww + inflate
                    and wy - inflate <= y_root <= wy + wh + inflate
                ):
                    return True
            except Exception:
                continue
        return False

    def _close_submenu(self) -> None:
        """只关掉当前级联子窗，保留主菜单。"""
        self._cancel_sub_close()
        sub = self._active_sub
        self._active_sub = None
        if sub is None:
            return
        try:
            if sub in self._wins:
                self._wins.remove(sub)
        except ValueError:
            pass
        try:
            if sub.winfo_exists():
                sub.destroy()
        except Exception:
            pass

    def _schedule_close_submenu(self) -> None:
        self._cancel_sub_close()

        def _go():
            self._sub_close_job = None
            # 指针仍在菜单（含重叠区）则保留
            try:
                x = self.master.winfo_pointerx()
                y = self.master.winfo_pointery()
                if self._point_in_menus(x, y, inflate=2):
                    return
            except Exception:
                pass
            self._close_submenu()

        self._sub_close_job = self.master.after(160, _go)

    def _make_shell(self) -> tuple[tk.Toplevel, tk.Frame]:
        win = tk.Toplevel(self.master)
        win.withdraw()
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        win.configure(bg=STROKE)
        outer = tk.Frame(win, bg=STROKE, bd=0, highlightthickness=0)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=BG2, bd=0, highlightthickness=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self._wins.append(win)
        # 进入任意菜单窗体时取消“延时关子菜单”
        win.bind("<Enter>", lambda _e: self._cancel_sub_close(), add="+")
        return win, inner

    def _add_separator(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg=STROKE, height=1)
        bar.pack(fill="x", padx=10, pady=5)

    def _clear_panel_hover(self, panel: tk.Frame, *, except_row: tk.Frame | None = None) -> None:
        """同级互斥：熄灭该面板内其它行的高亮。"""
        key = id(panel)
        cur = self._hover_row.get(key)
        for child in panel.winfo_children():
            if not isinstance(child, tk.Frame):
                continue
            clearer = getattr(child, "_set_active", None)
            if clearer is None:
                continue
            if except_row is not None and child is except_row:
                continue
            try:
                clearer(False)
            except Exception:
                pass
        if except_row is None:
            self._hover_row.pop(key, None)
        elif cur is not None and cur is not except_row:
            self._hover_row[key] = except_row

    def _add_item(
        self,
        parent: tk.Frame,
        label: str,
        *,
        command: Callable[[], None] | None = None,
        submenu: list | None = None,
        danger: bool = False,
        is_root_panel: bool = False,
    ) -> None:
        row = tk.Frame(parent, bg=BG2, height=ROW_H)
        row.pack(fill="x")
        row.pack_propagate(False)
        fg = "#F87171" if danger else TEXT
        text = f"{label}    ›" if submenu else f"  {label}"
        lab = tk.Label(
            row,
            text=text,
            anchor="w",
            bg=BG2,
            fg=fg,
            font=("Microsoft YaHei UI", 9),
            padx=PAD_X,
        )
        lab.pack(fill="both", expand=True)

        def set_active(on: bool) -> None:
            bg = ACTIVE if on else BG2
            color = ACCENT if on and not danger else fg
            try:
                row.configure(bg=bg)
                lab.configure(bg=bg, fg=color)
            except tk.TclError:
                pass
            key = id(parent)
            if on:
                self._hover_row[key] = row
            elif self._hover_row.get(key) is row:
                self._hover_row.pop(key, None)

        row._set_active = set_active  # type: ignore[attr-defined]

        def open_sub(_event=None) -> None:
            if not submenu:
                return
            self._cancel_sub_close()
            # 已打开同一子菜单则复用
            if self._active_sub is not None:
                try:
                    if self._active_sub.winfo_exists():
                        # 若已是当前行的子菜单，不重复建
                        if getattr(row, "_sub_win", None) is self._active_sub:
                            self._active_sub.lift()
                            return
                except Exception:
                    pass
                self._close_submenu()
            self._place_submenu(row, submenu)

        def on_enter(_e) -> None:
            # 先熄灭同级其它项，再点亮当前项（互斥高亮）
            self._clear_panel_hover(parent, except_row=row)
            set_active(True)
            self._cancel_sub_close()
            if submenu:
                open_sub()
            elif is_root_panel:
                # 悬停普通项时收起其它级联
                self._schedule_close_submenu()

        def on_leave(e) -> None:
            # 仍在本行内部（Label <-> Frame）不灭
            try:
                widget = e.widget.winfo_containing(e.x_root, e.y_root)
                if widget is not None:
                    w = widget
                    while w is not None:
                        if w is row:
                            return
                        w = getattr(w, "master", None)
            except Exception:
                pass
            # 滑向本行打开的子菜单：保留父项高亮，但不挡其它项互斥
            if submenu:
                sub = getattr(row, "_sub_win", None)
                if sub is not None:
                    try:
                        if sub.winfo_exists():
                            sx, sy = sub.winfo_rootx(), sub.winfo_rooty()
                            sw, sh = sub.winfo_width(), sub.winfo_height()
                            if (
                                sx - SUB_OVERLAP <= e.x_root <= sx + sw + 2
                                and sy - 2 <= e.y_root <= sy + sh + 2
                            ):
                                # 保留高亮，延后关子菜单由 schedule 判断
                                return
                    except Exception:
                        pass
            set_active(False)
            if submenu or is_root_panel:
                self._schedule_close_submenu()

        def on_click(_e) -> str:
            if submenu:
                open_sub()
                return "break"
            if self._invoked or self._closed:
                return "break"
            self._invoked = True
            self._log(f"dark_menu_click {label!r}")
            cmd = command
            self.close()
            try:
                if cmd:
                    cmd()
                    self._log(f"dark_menu_ok {label!r}")
            except Exception as ex:
                self._log(f"dark_menu_fail {label!r} {ex!r}")
            return "break"

        for w in (row, lab):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<ButtonPress-1>", on_click)

    def _place_submenu(self, anchor_row: tk.Frame, items: list) -> None:
        win, inner = self._make_shell()
        self._active_sub = win
        setattr(anchor_row, "_sub_win", win)
        for it in items:
            kind = it[0]
            if kind == "sep":
                self._add_separator(inner)
            elif kind == "item":
                self._add_item(inner, it[1], command=it[2], is_root_panel=False)
            elif kind == "cascade":
                self._add_item(inner, it[1], submenu=it[2], is_root_panel=False)

        win.update_idletasks()
        ww = max(MIN_W - 12, win.winfo_reqwidth())
        wh = win.winfo_reqheight()
        # 向父项重叠 SUB_OVERLAP，鼠标可滑入
        ax = anchor_row.winfo_rootx() + anchor_row.winfo_width() - SUB_OVERLAP
        ay = anchor_row.winfo_rooty() - 1
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        if ax + ww > sw - 8:
            ax = anchor_row.winfo_rootx() - ww + SUB_OVERLAP
        if ay + wh > sh - 8:
            ay = max(8, sh - wh - 8)
        if ay < 4:
            ay = 4
        win.geometry(f"{ww}x{wh}+{ax}+{ay}")
        win.deiconify()
        win.lift()
        self._log(f"submenu_at {ax},{ay} size={ww}x{wh}")

    def popup(self, x: int, y: int, spec: list) -> None:
        self._closed = False
        self._invoked = False
        self._active_sub = None
        self._hover_row.clear()
        win, inner = self._make_shell()
        for it in spec:
            kind = it[0]
            if kind == "sep":
                self._add_separator(inner)
            elif kind == "item":
                self._add_item(
                    inner,
                    it[1],
                    command=it[2],
                    danger=("退出" in it[1]),
                    is_root_panel=True,
                )
            elif kind == "cascade":
                self._add_item(inner, it[1], submenu=it[2], is_root_panel=True)

        win.update_idletasks()
        ww = max(MIN_W, win.winfo_reqwidth())
        wh = win.winfo_reqheight()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x = min(max(4, x), sw - ww - 4)
        y = min(max(4, y), sh - wh - 4)
        win.geometry(f"{ww}x{wh}+{x}+{y}")
        win.deiconify()
        win.lift()
        try:
            win.focus_force()
        except Exception:
            pass
        self._log(f"dark_popup_at {x},{y}")

        def _arm() -> None:
            # 不用 grab_set：会挡住子 Toplevel 的点击（级联点不中）
            DarkContextMenu._outside_armed = self
            DarkContextMenu._ensure_outside_handler(self.master)

        self._outside_job = self.master.after(220, _arm)
        win.bind("<Escape>", lambda _e: self.close())
