# -*- coding: utf-8 -*-
"""决策骰子 — 1~6 随机点子。"""

from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

BG, ACCENT, TEXT, MUTED = "#0B0F17", "#F5C542", "#E8EEF7", "#8B9BB4"
FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
HINTS = ["观望", "小试", "推进", "求助", "休息", "梭哈（谨慎）"]


class DiceView(tk.Frame):
    def __init__(self, master, *, width: int, height: int, on_back: Callable[[], None] | None = None):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(top, text="决策骰子", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        tk.Button(top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
                  font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2").pack(side="right")
        self.face = tk.Label(self, text="🎲", bg=BG, fg=TEXT, font=("Segoe UI Emoji", 56))
        self.face.pack(expand=True)
        self.msg = tk.Label(self, text="扔一下看运气", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 10))
        self.msg.pack(pady=4)
        tk.Button(self, text="扔骰子", command=self._roll, bg=ACCENT, fg="#1A1400", relief="flat",
                  font=("Microsoft YaHei UI", 9, "bold"), padx=12, pady=4, cursor="hand2").pack(pady=(0, 12))

    def _back(self):
        if self.on_back:
            self.on_back()

    def destroy_game(self):
        self.destroy()

    def _roll(self):
        n = random.randint(1, 6)
        self.face.configure(text=FACES[n - 1])
        self.msg.configure(text=f"{n} 点 · 建议：{HINTS[n - 1]}")
