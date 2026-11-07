# -*- coding: utf-8 -*-
"""井字棋 — 三子轮换；闪烁标出双方下一颗将消失的子。"""

from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

BG, CARD, ACCENT, TEXT, MUTED = "#0B0F17", "#1A2332", "#F5C542", "#E8EEF7", "#8B9BB4"
AI_COLOR = "#34D399"
WARN_BG = "#7F1D1D"
WARN_BG2 = "#3F1D1D"


class TicTacToeView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        width: int,
        height: int,
        on_back: Callable[[], None] | None = None,
    ):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self.board = [""] * 9
        self.order = {"X": [], "O": []}
        self.colors = {"X": ACCENT, "O": AI_COLOR}
        self.human, self.ai = "X", "O"
        self.over = False
        self._blink_on = False
        self._blink_job: str | None = None

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(top, text="井字棋·三子轮换", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        tk.Button(
            top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400",
            relief="flat", font=("Microsoft YaHei UI", 8), padx=6, pady=1, cursor="hand2",
        ).pack(side="right")

        self.status = tk.Label(
            self, text="红底闪烁 = 下一子落下时会消失", bg=BG, fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        self.status.pack(pady=(0, 2))

        grid = tk.Frame(self, bg=BG)
        grid.pack(expand=True)
        self.btns: list[tk.Button] = []
        for i in range(9):
            b = tk.Button(
                grid, text="", width=3, height=1, font=("Microsoft YaHei UI", 12, "bold"),
                bg=CARD, fg=TEXT, activebackground=ACCENT, relief="flat",
                command=lambda i=i: self._click(i),
            )
            b.grid(row=i // 3, column=i % 3, padx=3, pady=3, ipadx=4, ipady=4)
            self.btns.append(b)

        tk.Button(
            self, text="再来", command=self._reset, bg=CARD, fg=TEXT, relief="flat",
            font=("Microsoft YaHei UI", 8), padx=8, cursor="hand2",
        ).pack(pady=(2, 8))

        self._schedule_blink()

    def _back(self) -> None:
        self._stop_blink()
        if self.on_back:
            self.on_back()

    def destroy_game(self) -> None:
        self._stop_blink()
        self.destroy()

    def _stop_blink(self) -> None:
        if self._blink_job:
            try:
                self.after_cancel(self._blink_job)
            except Exception:
                pass
            self._blink_job = None

    def _next_vanish(self) -> set[int]:
        """双方各若已有 3 子，则最早那颗即为下一颗将消失的。"""
        out: set[int] = set()
        for mark in ("X", "O"):
            if len(self.order[mark]) >= 3:
                out.add(self.order[mark][0])
        return out

    def _schedule_blink(self) -> None:
        self._blink_on = not self._blink_on
        self._refresh_warn_styles()
        try:
            if self.winfo_exists() and not self.over:
                self._blink_job = self.after(420, self._schedule_blink)
            else:
                self._blink_job = None
        except tk.TclError:
            self._blink_job = None

    def _refresh_warn_styles(self) -> None:
        vanish = self._next_vanish() if not self.over else set()
        for i, b in enumerate(self.btns):
            mark = self.board[i]
            if not mark:
                b.configure(bg=CARD, fg=TEXT)
                continue
            color = self.colors.get(mark, TEXT)
            if i in vanish:
                # 闪烁红底提醒「下一颗会消失」
                b.configure(bg=WARN_BG if self._blink_on else WARN_BG2, fg=color)
            else:
                b.configure(bg=CARD, fg=color)

    def _reset(self) -> None:
        self.board = [""] * 9
        self.order = {"X": [], "O": []}
        self.over = False
        for b in self.btns:
            b.configure(text="", state="normal", fg=TEXT, bg=CARD)
        self.status.configure(text="再战！红底闪烁子下一颗会消失")
        self._stop_blink()
        self._schedule_blink()

    def _click(self, i: int) -> None:
        if self.over or self.board[i]:
            return
        self._place(i, self.human)
        if self._finish(self.human, "你赢了"):
            return
        self.after(120, self._ai_move)

    def _ai_move(self) -> None:
        if self.over:
            return
        move = self._best()
        if move is None:
            return
        self._place(move, self.ai)
        self._finish(self.ai, "AI 赢了")

    def _place(self, i: int, mark: str) -> None:
        self.board[i] = mark
        self.order[mark].append(i)
        self.btns[i].configure(text=mark, fg=self.colors[mark], state="disabled", bg=CARD)
        if len(self.order[mark]) > 3:
            old = self.order[mark].pop(0)
            self.board[old] = ""
            self.btns[old].configure(text="", state="normal", fg=TEXT, bg=CARD)
        self._refresh_warn_styles()

    def _finish(self, mark: str, msg: str) -> bool:
        if self._winner(mark):
            self.over = True
            self.status.configure(text=msg)
            self._refresh_warn_styles()
            return True
        return False

    def _winner(self, m: str) -> bool:
        lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        return any(self.board[a] == self.board[b] == self.board[c] == m for a,b,c in lines)

    def _best(self) -> int | None:
        empties = [i for i, v in enumerate(self.board) if not v]
        if not empties:
            return None
        for m in (self.ai, self.human):
            for i in empties:
                saved_board = self.board[:]
                saved_order = {k: v[:] for k, v in self.order.items()}
                self.board[i] = m
                self.order[m].append(i)
                if len(self.order[m]) > 3:
                    old = self.order[m].pop(0)
                    self.board[old] = ""
                win = self._winner(m)
                self.board = saved_board
                self.order = saved_order
                if win:
                    return i
        for i in [4, 0, 2, 6, 8, 1, 3, 5, 7]:
            if i in empties:
                return i
        return random.choice(empties)
