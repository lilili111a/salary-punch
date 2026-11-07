# -*- coding: utf-8 -*-
"""命运硬币 — 做 / 不做。"""

from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

BG, CARD, ACCENT, TEXT, MUTED = "#0B0F17", "#1A2332", "#F5C542", "#E8EEF7", "#8B9BB4"


class CoinView(tk.Frame):
    def __init__(self, master, *, width: int, height: int, on_back: Callable[[], None] | None = None):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self._job = None
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(top, text="命运硬币", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        tk.Button(top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
                  font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2").pack(side="right")
        tk.Label(self, text="犹豫要不要做？交给硬币", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8)).pack()
        self.coin = tk.Label(self, text="🪙", bg=BG, fg=ACCENT, font=("Segoe UI Emoji", 52))
        self.coin.pack(expand=True)
        self.result = tk.Label(self, text="点下方抛一次", bg=CARD, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold"), padx=16, pady=8)
        self.result.pack(pady=6)
        tk.Button(
            self, text="抛硬币：做 / 不做", command=self._flip, bg=ACCENT, fg="#1A1400", relief="flat",
            font=("Microsoft YaHei UI", 9, "bold"), padx=12, pady=4, cursor="hand2",
        ).pack(pady=(0, 12))

    def _back(self):
        if self.on_back:
            self.on_back()

    def destroy_game(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self.destroy()

    def _flip(self):
        frames = ["🪙", "✨", "🪙", "✨", "🪙"]
        def spin(i=0):
            if i < len(frames):
                self.coin.configure(text=frames[i])
                self.result.configure(text="命运旋转中…")
                self._job = self.after(70, lambda: spin(i + 1))
            else:
                do = random.random() < 0.5
                self.coin.configure(text="🪙")
                self.result.configure(
                    text="去做！" if do else "先别做",
                    fg="#34D399" if do else "#FB7185",
                )
        spin()
