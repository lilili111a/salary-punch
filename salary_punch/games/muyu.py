# -*- coding: utf-8 -*-
"""敲木鱼 — 圆鼓形木鱼 + 木槌，卡片内解压。"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Callable

BG, ACCENT, TEXT, MUTED = "#0B0F17", "#F5C542", "#E8EEF7", "#8B9BB4"
WOOD = "#8B5A2B"
WOOD_DARK = "#5C3A1E"
WOOD_LIGHT = "#C4A484"
GOLD = "#E8C36A"


class MuyuView(tk.Frame):
    def __init__(self, master, *, width: int, height: int, on_back: Callable[[], None] | None = None):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self.count = 0
        self._pulse = None
        self._angle = -35  # mallet angle degrees
        self.W, self.H = width, height - 70

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(top, text="敲木鱼", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        tk.Button(top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
                  font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2").pack(side="right")
        self.hint = tk.Label(self, text="功德 +0 · 点击木鱼或木槌", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9))
        self.hint.pack(pady=2)

        self.canvas = tk.Canvas(self, width=width, height=self.H, bg=BG, highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._hit)
        self._draw(rest=True)
        tk.Label(self, text="带薪积德，合法解压", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8)).pack(pady=(0, 8))

    def _back(self):
        if self.on_back:
            self.on_back()

    def destroy_game(self):
        if self._pulse:
            try:
                self.after_cancel(self._pulse)
            except Exception:
                pass
        self.destroy()

    def _draw(self, rest: bool = True) -> None:
        c = self.canvas
        c.delete("all")
        cx, cy = self.W // 2 if hasattr(self, 'W') else 154, self.H // 2 + 8
        # actually width from canvas
        cw = int(c.cget("width"))
        ch = int(c.cget("height"))
        cx, cy = cw // 2, ch // 2 + 6
        # wooden fish body — rounded fish-drum
        rx, ry = 58, 42
        c.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill=WOOD, outline=WOOD_DARK, width=3)
        c.create_oval(cx - rx + 10, cy - ry + 8, cx + rx - 8, cy + ry - 10, fill=WOOD_LIGHT, outline="")
        # mouth slit
        c.create_arc(cx - 18, cy - 8, cx + 22, cy + 28, start=200, extent=140, style="arc", outline=WOOD_DARK, width=3)
        # eye
        c.create_oval(cx + 18, cy - 18, cx + 30, cy - 6, fill="#1A1400", outline="")
        c.create_oval(cx + 21, cy - 15, cx + 25, cy - 11, fill="#F5F5F5", outline="")
        # scale lines
        for i in range(-2, 3):
            c.create_arc(cx - 40, cy - 20 + i * 8, cx + 10, cy + 20 + i * 8, start=30, extent=100, style="arc", outline=WOOD_DARK, width=1)
        # stand
        c.create_rectangle(cx - 16, cy + ry - 4, cx + 16, cy + ry + 10, fill=WOOD_DARK, outline="")

        # mallet
        ang = -55 if rest else -15
        rad = math.radians(ang)
        hx, hy = cx - 70, cy - 10
        L = 70
        ex = hx + L * math.cos(rad)
        ey = hy + L * math.sin(rad)
        c.create_line(hx, hy, ex, ey, fill="#A67C52", width=6, capstyle="round")
        # mallet head
        c.create_oval(ex - 10, ey - 10, ex + 10, ey + 10, fill=GOLD, outline=WOOD_DARK, width=2)
        c.create_text(cx, ch - 12, text="木鱼", fill=MUTED, font=("Microsoft YaHei UI", 8))

    def _hit(self, _e=None):
        self.count += 1
        self.hint.configure(text=f"功德 +{self.count} · 心静了吗？")
        self._draw(rest=False)
        if self._pulse:
            try:
                self.after_cancel(self._pulse)
            except Exception:
                pass
        self._pulse = self.after(100, lambda: self._draw(rest=True))
