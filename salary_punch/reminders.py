# -*- coding: utf-8 -*-
"""空闲一段时间后，不定期弹出关怀/摸鱼提醒（卡片内文案）。"""

from __future__ import annotations

import random
import time

REMINDERS = [
    "该喝水了，干了这杯再搬砖 💧",
    "起来走走，血赚不误活动筋骨",
    "该带薪摸鱼了，合法休息一下",
    "看看远处，让眼睛歇 20 秒",
    "深呼吸三次，再继续冲",
    "去倒杯水吧，工位会想你的",
    "站起来伸个懒腰，钱包支持你",
    "摸鱼提醒：人要对自己好一点",
    "久坐预警：腿还在吗？活动一下",
    "茶/咖啡续上，效率续命",
    "上个厕所也算带薪巡回",
    "窗外望一眼，世界还很大",
]


class ReminderScheduler:
    """基于空闲秒数 + 随机冷却，决定是否弹出下一条。"""

    def __init__(self) -> None:
        now = time.time()
        self.last_active = now
        self.last_shown = 0.0
        self.min_idle = 7 * 60  # 至少空闲 7 分钟才考虑
        self.cooldown = (4 * 60, 12 * 60)  # 两次提醒间隔 4–12 分钟随机
        self._next_gap = random.uniform(*self.cooldown)
        self._last_text = ""

    def poke(self) -> None:
        self.last_active = time.time()

    def maybe_pick(self) -> str | None:
        now = time.time()
        idle = now - self.last_active
        if idle < self.min_idle:
            return None
        if now - self.last_shown < self._next_gap:
            return None
        # 不定期：空闲越久概率略升，但仍随机
        chance = 0.55 + min(0.35, (idle - self.min_idle) / 1200.0)
        if random.random() > chance:
            # 未命中：短推迟后再试，保持不定期
            self.last_shown = now - self._next_gap + random.uniform(45, 120)
            return None
        pool = [t for t in REMINDERS if t != self._last_text] or REMINDERS
        text = random.choice(pool)
        self._last_text = text
        self.last_shown = now
        self._next_gap = random.uniform(*self.cooldown)
        return text
