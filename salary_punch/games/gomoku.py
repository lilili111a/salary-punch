# -*- coding: utf-8 -*-
"""五子棋 — 15路；小棋子塞满卡片；强化威胁评估 AI。"""

from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

BG, LINE, BLACK, WHITE, ACCENT, MUTED = "#0B0F17", "#4A3728", "#1A1A1A", "#FAFAFA", "#F5C542", "#8B9BB4"
BOARD_BG = "#E8D4A8"  # 浅木色素净底板
N = 15
DIRS = ((1, 0), (0, 1), (1, 1), (1, -1))

# pattern scores
SCORE_WIN = 1000000
SCORE_LIVE4 = 100000
SCORE_RUSH4 = 20000
SCORE_LIVE3 = 8000
SCORE_RUSH3 = 2000
SCORE_LIVE2 = 600
SCORE_RUSH2 = 150
SCORE_LIVE1 = 30


class GomokuView(tk.Frame):
    def __init__(self, master, *, width: int, height: int, on_back: Callable[[], None] | None = None):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self.board = [[0] * N for _ in range(N)]
        self.over = False
        # 15 路：尽量塞满卡片可用区，棋子缩小
        avail_w = width - 16
        avail_h = height - 52
        self.cell = max(10, min(avail_w, avail_h) // (N - 1))
        self.margin = max(6, (min(avail_w, avail_h) - self.cell * (N - 1)) // 2)

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(top, text="五子棋·15路", bg=BG, fg="#E8EEF7", font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        tk.Button(
            top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400",
            relief="flat", font=("Microsoft YaHei UI", 8), padx=6, pady=1, cursor="hand2",
        ).pack(side="right")
        self.status = tk.Label(self, text="你执黑 · 标准五子连珠", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8))
        self.status.pack()
        size = self.cell * (N - 1) + self.margin * 2
        self.canvas = tk.Canvas(self, width=size, height=size, bg=BOARD_BG, highlightthickness=0)
        self.canvas.pack(pady=1)
        self.canvas.bind("<Button-1>", self._click)
        self._draw_board()
        tk.Button(
            self, text="重开", command=self._reset, bg="#1A2332", fg="#E8EEF7", relief="flat",
            font=("Microsoft YaHei UI", 8), padx=8, cursor="hand2",
        ).pack(pady=(1, 4))

    def _back(self) -> None:
        if self.on_back:
            self.on_back()

    def destroy_game(self) -> None:
        self.destroy()

    def _reset(self) -> None:
        self.board = [[0] * N for _ in range(N)]
        self.over = False
        self.status.configure(text="再来！你执黑")
        self._draw_board()

    def _draw_board(self) -> None:
        c = self.canvas
        c.delete("all")
        m, cell = self.margin, self.cell
        # 浅木色纯底板 + 清晰深色格线（无花纹）
        c.create_rectangle(0, 0, int(c.cget("width")), int(c.cget("height")), fill=BOARD_BG, outline="")
        for i in range(N):
            c.create_line(m, m + i * cell, m + (N - 1) * cell, m + i * cell, fill=LINE, width=1)
            c.create_line(m + i * cell, m, m + i * cell, m + (N - 1) * cell, fill=LINE, width=1)
        # 天元小点，便于定位
        star = {3, N // 2, N - 4} if N >= 13 else {N // 2}
        for y in star:
            for x in star:
                cx, cy = m + x * cell, m + y * cell
                c.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=LINE, outline="")
        for y in range(N):
            for x in range(N):
                if self.board[y][x]:
                    self._stone(x, y, self.board[y][x])

    def _stone(self, x: int, y: int, who: int) -> None:
        m, cell = self.margin, self.cell
        cx, cy = m + x * cell, m + y * cell
        r = max(3.5, cell * 0.36)
        color = BLACK if who == 1 else WHITE
        outline = "#111111" if who == 1 else "#333333"
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=outline, width=1)

    def _click(self, e) -> None:
        if self.over:
            return
        m, cell = self.margin, self.cell
        x = int(round((e.x - m) / cell))
        y = int(round((e.y - m) / cell))
        if not (0 <= x < N and 0 <= y < N) or self.board[y][x]:
            return
        self.board[y][x] = 1
        self._stone(x, y, 1)
        if self._win_at(x, y, 1):
            self.over = True
            self.status.configure(text="你赢了！难得")
            return
        self.status.configure(text="AI 思考中…")
        self.after(40, self._ai)

    def _ai(self) -> None:
        if self.over:
            return
        move = self._pick()
        if not move:
            self.over = True
            self.status.configure(text="棋盘满了")
            return
        x, y = move
        self.board[y][x] = 2
        self._stone(x, y, 2)
        if self._win_at(x, y, 2):
            self.over = True
            self.status.configure(text="AI 五连，再试一盘")
        else:
            self.status.configure(text="轮到你了")

    def _win_at(self, x: int, y: int, who: int) -> bool:
        for dx, dy in DIRS:
            cnt = 1
            for s in (1, -1):
                nx, ny = x + dx * s, y + dy * s
                while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == who:
                    cnt += 1
                    nx += dx * s
                    ny += dy * s
            if cnt >= 5:
                return True
        return False

    def _line_score(self, x: int, y: int, dx: int, dy: int, who: int) -> int:
        """评估落子后该方向的威胁。"""
        opp = 3 - who
        # count consecutive including (x,y)
        left = 0
        nx, ny = x - dx, y - dy
        while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == who:
            left += 1
            nx -= dx
            ny -= dy
        right = 0
        nx, ny = x + dx, y + dy
        while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == who:
            right += 1
            nx += dx
            ny += dy
        length = left + right + 1
        # open ends
        lx, ly = x - dx * (left + 1), y - dy * (left + 1)
        rx, ry = x + dx * (right + 1), y + dy * (right + 1)
        left_open = 0 <= lx < N and 0 <= ly < N and self.board[ly][lx] == 0
        right_open = 0 <= rx < N and 0 <= ry < N and self.board[ry][rx] == 0
        # blocked by wall/opponent
        if not (0 <= lx < N and 0 <= ly < N):
            left_open = False
        elif self.board[ly][lx] == opp:
            left_open = False
        if not (0 <= rx < N and 0 <= ry < N):
            right_open = False
        elif self.board[ry][rx] == opp:
            right_open = False
        opens = (1 if left_open else 0) + (1 if right_open else 0)
        if length >= 5:
            return SCORE_WIN
        if length == 4:
            return SCORE_LIVE4 if opens == 2 else (SCORE_RUSH4 if opens == 1 else 0)
        if length == 3:
            return SCORE_LIVE3 if opens == 2 else (SCORE_RUSH3 if opens == 1 else 0)
        if length == 2:
            return SCORE_LIVE2 if opens == 2 else (SCORE_RUSH2 if opens == 1 else 0)
        if length == 1:
            return SCORE_LIVE1 if opens >= 1 else 0
        return 0

    def _point_score(self, x: int, y: int, who: int) -> int:
        if self.board[y][x] != 0:
            return -1
        self.board[y][x] = who
        s = 0
        for dx, dy in DIRS:
            s += self._line_score(x, y, dx, dy, who)
        self.board[y][x] = 0
        # center bias
        mid = N // 2
        s += max(0, 6 - (abs(x - mid) + abs(y - mid))) * 3
        return s

    def _candidates(self) -> list[tuple[int, int]]:
        stones = [(x, y) for y in range(N) for x in range(N) if self.board[y][x]]
        if not stones:
            return [(N // 2, N // 2)]
        cands = set()
        for x, y in stones:
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == 0:
                        cands.add((nx, ny))
        return list(cands) or [(x, y) for y in range(N) for x in range(N) if self.board[y][x] == 0]

    def _pick(self):
        cands = self._candidates()
        scored: list[tuple[float, int, int]] = []
        for x, y in cands:
            self.board[y][x] = 2
            if self._win_at(x, y, 2):
                self.board[y][x] = 0
                return x, y
            self.board[y][x] = 0
            atk = self._point_score(x, y, 2)
            dfn = self._point_score(x, y, 1)
            score = atk * 1.05 + dfn * 1.2
            self.board[y][x] = 1
            if self._win_at(x, y, 1):
                score += SCORE_WIN * 0.6  # 必防
            self.board[y][x] = 0
            scored.append((score, x, y))
        scored.sort(reverse=True)
        top = scored[:12]
        refined: list[tuple[float, int, int]] = []
        for base, x, y in top:
            self.board[y][x] = 2
            reply_best = 0.0
            for cx, cy in self._candidates():
                self.board[cy][cx] = 1
                threat = SCORE_WIN if self._win_at(cx, cy, 1) else float(self._point_score(cx, cy, 1))
                self.board[cy][cx] = 0
                if threat > reply_best:
                    reply_best = threat
            self.board[y][x] = 0
            refined.append((base - reply_best * 0.4, x, y))
        refined.sort(reverse=True)
        lead = refined[0][0]
        pool = [(x, y) for sc, x, y in refined if sc >= lead - 800]
        return random.choice(pool)
