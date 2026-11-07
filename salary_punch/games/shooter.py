# -*- coding: utf-8 -*-
"""Q版雷霆战机 — 掉落升级；无盾被碰3次结束；后期敌机多路径。"""

from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Callable

BG = "#0B0F17"
ACCENT = "#F5C542"
POWER_TYPES = ("fire", "multi", "shield", "speed")
POWER_LABEL = {"fire": "火力", "multi": "散射", "shield": "护盾", "speed": "加速"}
POWER_COLOR = {"fire": "#F97316", "multi": "#A78BFA", "shield": "#38BDF8", "speed": "#4ADE80"}


class ShooterView(tk.Frame):
    def __init__(self, master, *, width: int, height: int, on_back: Callable[[], None] | None = None):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self.W = width
        self.H = height - 28

        top = tk.Frame(self, bg=BG, height=28)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="Q战机 ←→/AD 空格 · 无盾3命", bg=BG, fg="#8B9BB4", font=("Microsoft YaHei UI", 8)).pack(side="left", padx=8)
        tk.Button(top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
                  font=("Microsoft YaHei UI", 8), padx=6, pady=1, cursor="hand2").pack(side="right", padx=8)

        self.canvas = tk.Canvas(self, width=self.W, height=self.H, bg="#0B1220", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.px = self.W // 2
        self.py = self.H - 36
        self.bullets: list[list[float]] = []
        # enemy: x,y,spd,hp,kind,pattern,phase,base_x,vx
        self.enemies: list[list] = []
        self.powers: list[list] = []
        self.stars = [[random.randint(0, self.W), random.randint(0, self.H), random.random()] for _ in range(28)]
        self.score = 0
        self.lives = 3
        self.alive = True
        self.game_over = False
        self.keys: set[str] = set()
        self._job = None
        self._cool = 0
        self.fire = 1
        self.multi = 1
        self.shield = 0
        self.speed = 6.0
        self._flash = 0

        for w in (self, self.canvas, top):
            w.bind("<KeyPress>", self._down)
            w.bind("<KeyRelease>", self._up)
        self.canvas.focus_set()
        self.bind("<Button-1>", lambda _e: self.canvas.focus_set())
        self._tick()

    def _back(self) -> None:
        self.alive = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        if self.on_back:
            self.on_back()

    def destroy_game(self) -> None:
        self.alive = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self.destroy()

    def _down(self, e) -> None:
        if self.game_over and e.keysym in ("Return", "r", "R", "space"):
            self._restart()
            return
        self.keys.add(e.keysym)

    def _up(self, e) -> None:
        self.keys.discard(e.keysym)

    def _restart(self) -> None:
        self.px, self.py = self.W // 2, self.H - 36
        self.bullets.clear()
        self.enemies.clear()
        self.powers.clear()
        self.score = 0
        self.lives = 3
        self.fire = 1
        self.multi = 1
        self.shield = 0
        self.speed = 6.0
        self._flash = 0
        self.game_over = False
        self._cool = 0

    def _tick(self) -> None:
        if not self.alive:
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if not self.game_over:
            self._update()
        self._draw()
        self._job = self.after(33, self._tick)

    def _shoot(self) -> None:
        lanes = min(3, self.multi)
        spreads = {1: [0], 2: [-3, 3], 3: [-4, 0, 4]}[lanes]
        for dx in spreads:
            self.bullets.append([self.px, self.py - 14, float(dx)])

    def _pick_pattern(self) -> str:
        if self.score < 80:
            return "down"
        if self.score < 180:
            return random.choice(("down", "down", "sine", "diag"))
        if self.score < 320:
            return random.choice(("sine", "diag", "zigzag", "down"))
        return random.choice(("sine", "diag", "zigzag", "circle", "sine"))

    def _spawn_enemy(self) -> None:
        hp = 1 + (1 if random.random() < 0.22 + min(0.35, self.score * 0.0004) else 0)
        kind = "elite" if hp > 1 else "norm"
        pattern = self._pick_pattern()
        x = random.randint(24, self.W - 24)
        spd = random.uniform(1.6, 2.8 + min(2.0, self.score / 600))
        vx = random.choice((-1.0, 1.0)) * random.uniform(1.2, 2.4)
        self.enemies.append([float(x), -16.0, spd, hp, kind, pattern, 0.0, float(x), vx])

    def _move_enemy(self, en: list) -> None:
        pattern = en[5]
        en[6] += 0.12
        en[1] += en[2]
        if pattern == "down":
            return
        if pattern == "sine":
            amp = 28 + min(40, self.score / 20)
            en[0] = en[7] + math.sin(en[6] * 1.6) * amp
            en[0] = max(16, min(self.W - 16, en[0]))
        elif pattern == "diag":
            en[0] += en[8]
            if en[0] < 16 or en[0] > self.W - 16:
                en[8] *= -1
                en[0] = max(16, min(self.W - 16, en[0]))
        elif pattern == "zigzag":
            if int(en[6] * 4) % 8 < 4:
                en[0] += abs(en[8])
            else:
                en[0] -= abs(en[8])
            en[0] = max(16, min(self.W - 16, en[0]))
        elif pattern == "circle":
            r = 22 + min(30, self.score / 30)
            en[0] = en[7] + math.cos(en[6] * 2.2) * r
            en[1] += math.sin(en[6] * 2.2) * 0.8
            en[0] = max(16, min(self.W - 16, en[0]))

    def _hit_player(self) -> None:
        if self.shield > 0:
            self.shield -= 1
            self._flash = 8
            return
        self.lives -= 1
        self._flash = 10
        if self.lives <= 0:
            self.lives = 0
            self.game_over = True
            self.enemies.clear()
            self.bullets.clear()
            self.powers.clear()

    def _update(self) -> None:
        sp = self.speed
        if "Left" in self.keys or "a" in self.keys or "A" in self.keys:
            self.px = max(18, self.px - sp)
        if "Right" in self.keys or "d" in self.keys or "D" in self.keys:
            self.px = min(self.W - 18, self.px + sp)
        self._cool = max(0, self._cool - 1)
        if "space" in self.keys and self._cool == 0:
            self._shoot()
            self._cool = max(4, 10 - self.fire)

        for b in self.bullets:
            b[0] += b[2]
            b[1] -= 9 + self.fire
        self.bullets = [b for b in self.bullets if -10 < b[1] < self.H + 20 and -20 < b[0] < self.W + 20]

        if random.random() < 0.035 + min(0.08, self.score * 0.00055):
            self._spawn_enemy()

        for en in self.enemies:
            self._move_enemy(en)

        new_bullets = []
        for b in self.bullets:
            used = False
            for en in self.enemies:
                if en[3] <= 0:
                    continue
                if abs(b[0] - en[0]) < 14 and abs(b[1] - en[1]) < 14:
                    en[3] -= max(1, self.fire // 2 + 1)
                    used = True
                    break
            if not used:
                new_bullets.append(b)
        self.bullets = new_bullets

        remain = []
        for en in self.enemies:
            if en[3] <= 0:
                self.score += 15 if en[4] == "elite" else 10
                if random.random() < (0.4 if en[4] == "elite" else 0.2):
                    self.powers.append([en[0], en[1], random.choice(POWER_TYPES)])
                continue
            if abs(en[0] - self.px) < 16 and abs(en[1] - self.py) < 16:
                self._hit_player()
                continue
            if -40 < en[1] < self.H + 30:
                remain.append(en)
        self.enemies = remain

        for p in self.powers:
            p[1] += 2.2
        kept = []
        for p in self.powers:
            if abs(p[0] - self.px) < 18 and abs(p[1] - self.py) < 18:
                self._apply_power(p[2])
                self.score += 5
                continue
            if p[1] < self.H + 10:
                kept.append(p)
        self.powers = kept

        for s in self.stars:
            s[1] += 1.2 + s[2] * 1.8
            if s[1] > self.H:
                s[0] = random.randint(0, self.W)
                s[1] = 0
        if self._flash:
            self._flash -= 1

    def _apply_power(self, kind: str) -> None:
        if kind == "fire":
            self.fire = min(5, self.fire + 1)
        elif kind == "multi":
            self.multi = min(3, self.multi + 1)
        elif kind == "shield":
            self.shield = min(3, self.shield + 1)
        elif kind == "speed":
            self.speed = min(11.0, self.speed + 1.2)

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")
        for s in self.stars:
            c.create_oval(s[0], s[1], s[0] + 2, s[1] + 2, fill="#6B7C99", outline="")
        for p in self.powers:
            col = POWER_COLOR[p[2]]
            c.create_oval(p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9, fill=col, outline="#fff")
            c.create_text(p[0], p[1], text=POWER_LABEL[p[2]][0], fill="#0B1220", font=("Microsoft YaHei UI", 7, "bold"))
        for en in self.enemies:
            fill = "#FB7185" if en[4] == "norm" else "#F43F5E"
            c.create_oval(en[0] - 10, en[1] - 9, en[0] + 10, en[1] + 9, fill=fill, outline="#FDA4AF")
            c.create_text(en[0], en[1], text=("鱼" if en[4] == "norm" else "Boss"), fill="#fff", font=("Microsoft YaHei UI", 7, "bold"))
        for b in self.bullets:
            r = 2 + self.fire * 0.6
            c.create_oval(b[0] - r, b[1] - 6, b[0] + r, b[1] + 1, fill="#FBBF24", outline="")
        x, y = self.px, self.py
        body = "#5EEAD4" if self._flash % 2 == 0 else "#FCA5A5"
        c.create_oval(x - 12, y - 10, x + 12, y + 10, fill=body, outline="#99F6E4")
        c.create_oval(x - 6, y - 16, x + 6, y - 4, fill="#F5C542", outline="")
        if self.shield > 0:
            c.create_oval(x - 18, y - 18, x + 18, y + 16, outline="#38BDF8", width=2)
        hearts = "♥" * self.lives + "♡" * max(0, 3 - self.lives)
        hud = f"{hearts} 分{self.score} 火{self.fire} 散{self.multi} 盾{self.shield} 速{self.speed:.0f}"
        c.create_text(8, 8, text=hud, fill="#E8EEF7", anchor="w", font=("Microsoft YaHei UI", 8, "bold"))
        if self.game_over:
            c.create_rectangle(20, self.H // 2 - 36, self.W - 20, self.H // 2 + 36, fill="#0F172A", outline=ACCENT)
            c.create_text(self.W // 2, self.H // 2 - 10, text=f"游戏结束 · 得分 {self.score}", fill=ACCENT, font=("Microsoft YaHei UI", 11, "bold"))
            c.create_text(self.W // 2, self.H // 2 + 14, text="按 R / 回车 / 空格 再来", fill="#8B9BB4", font=("Microsoft YaHei UI", 8))
