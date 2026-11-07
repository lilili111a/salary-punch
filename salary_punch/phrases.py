# -*- coding: utf-8 -*-
"""按时段挑选轻松话术：同段内粘滞，偶尔换一句，不每秒乱跳。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime

from .config import hhmm_to_minutes


# 每个时段的文案池（轻松有趣，别油腻）
POOLS: dict[str, list[str]] = {
    "rest": [
        "今天休息，工资也在躺平",
        "休假模式：薪资暂停营业",
        "休息日，好好充电",
        "不上班的日子，心情加倍",
    ],
    "fishing": [
        "摸鱼中：时间在走，钱也在走",
        "正经摸鱼，血赚进行时",
        "摸鱼半小时，工资也摸半小时",
        "老板：在忙吗？ 你：在赚钱",
        "鱼摸得越大，钱包越安心",
        "摸鱼状态已开启，请勿打扰",
    ],
    "paused": [
        "计时暂停中，摸鱼合法化",
        "今日工资按下了暂停键",
        "暂停计时 · 世界暂时静止",
    ],
    "need_punch": [
        "还没打卡，点一下开始进账",
        "打个卡，钱包才肯醒",
        "上班打卡后，秒数才值钱",
    ],
    "before": [
        "开工前夕，蓄势待发",
        "再喝口水，准备开赚",
        "工位就位，工资在路上",
    ],
    "morning_start": [
        "刚上班，今天也请加油",
        "开机成功，薪资开始滴答",
        "早起的鸟儿有工资拿",
        "新的一天，从第一分钱开始",
    ],
    "morning": [
        "上午稳步推进中",
        "要不然摸会鱼吧",
        "咖啡续上，效率续上",
        "邮件山在爬，工资也在爬",
        "安静搬砖，暗中进账",
    ],
    "pre_lunch": [
        "午饭将近，坚持一下",
        "胃在抗议，钱包在偷笑",
        "再扛一会儿就开饭",
        "午饭倒计时开启",
    ],
    "lunch": [
        "午休中，薪资小憩一下",
        "干饭时间，钱包旁观",
        "吃饱了才有力气赚钱",
        "午休合法，摸鱼加分",
    ],
    "after_lunch": [
        "午饭后有点困，眨眨眼",
        "午后犯困警告",
        "咖啡续命，工资续航",
        "眼皮打架，薪水加油",
    ],
    "afternoon": [
        "下午攻坚时间到",
        "下午好，继续稳稳进账",
        "要不然摸会鱼吧",
        "专注一会儿，钱包谢谢你",
        "下午场：效率与摸鱼并存",
    ],
    "near_off": [
        "坚持一下，快下班了",
        "终点线就在眼前",
        "再撑一会儿就自由了",
        "下班倒计时，稳住别浪",
        "快到点了，收尾要紧",
    ],
    "overtime": [
        "加班辛苦了，倍率已就位",
        "夜深了，工资多走一程",
        "加班中：每分钟都更值钱",
        "留下来的人，薪水懂你",
    ],
    "after_work": [
        "下班啦，今日到手已锁定",
        "收工！今天稳稳入账",
        "打卡下班，钱包满意",
        "今日份努力，已折现完毕",
    ],
    "payday_today": [
        "今天发薪日，心情额外好",
        "发薪日到，钱包准备开张",
        "今天发薪，笑容自己会上线",
    ],
    "payday_soon": [
        "发薪临近，再撑几天",
        "距离到手又近一步",
        "发薪倒计时进行中",
    ],
    "high_earn": [
        "今日到手不错嘛",
        "这一天真的有点赚",
        "钱包：今天表现可以",
        "进账喜人，继续保持",
    ],
}


@dataclass
class _Sticky:
    segment: str = ""
    text: str = ""
    until: float = 0.0
    last_idx: int = -1


_state = _Sticky()


def resolve_segment(
    *,
    now: datetime,
    is_workday: bool,
    is_paused: bool,
    auto: bool,
    has_in: bool,
    work_start: str,
    work_end: str,
    lunch_start: str,
    lunch_end: str,
    deduct_lunch: bool,
    clock_out: bool,
    day_done: bool = False,
    is_fishing: bool = False,
) -> str:
    if not is_workday:
        return "rest"
    if is_paused:
        return "paused"
    if is_fishing:
        return "fishing"
    if not auto and not has_in:
        return "need_punch"

    m = now.hour * 60 + now.minute + now.second / 60.0
    ws = hhmm_to_minutes(work_start)
    we = hhmm_to_minutes(work_end)
    ls = hhmm_to_minutes(lunch_start)
    le = hhmm_to_minutes(lunch_end)

    if clock_out or day_done:
        # 自动排班跨过下班点 → 下班文案；主动留下继续算加班时用 overtime
        if (not clock_out) and auto and m >= we and m < we + 15:
            return "after_work"
        if clock_out or (auto and m >= we):
            # 若仍想强调加班：超过下班 15 分钟且未打卡下班 → overtime
            if (not clock_out) and m >= we + 15:
                return "overtime"
            return "after_work"
    if m < ws:
        return "before"
    if m >= we:
        return "overtime"

    if deduct_lunch and ls <= m < le:
        return "lunch"

    # morning: start -> lunch
    if m < ls if deduct_lunch else m < (ws + we) / 2:
        if m < ws + 60:
            return "morning_start"
        if deduct_lunch and m >= ls - 45:
            return "pre_lunch"
        return "morning"

    # afternoon
    if m < we - 60:
        if deduct_lunch and m < le + 50:
            return "after_lunch"
        return "afternoon"
    return "near_off"


def pick_phrase(
    segment: str,
    *,
    payday_countdown: int = 99,
    today_progress: float = 0.0,
    today_earned: float = 0.0,
    daily_rate: float = 0.0,
    force: bool = False,
) -> tuple[str, str]:
    """返回 (segment_used, text)。同段粘滞 3~8 分钟；偶尔插入发薪/高进账彩蛋。"""
    now_ts = time.time()
    seg = segment

    # 轻量彩蛋覆盖（不打断粘滞太狠：仅当粘滞到期或 force）
    overlay = None
    if payday_countdown == 0 and segment not in ("rest", "paused"):
        overlay = "payday_today"
    elif 0 < payday_countdown <= 3 and segment not in ("rest", "paused", "before"):
        # 小概率在粘滞刷新时用发薪文案
        overlay = "payday_soon"
    elif (
        daily_rate > 0
        and today_earned >= daily_rate * 0.55
        and today_progress >= 0.55
        and segment in ("afternoon", "near_off", "overtime", "morning")
    ):
        overlay = "high_earn"

    use_seg = seg
    sticky_alive = (
        not force
        and _state.segment == use_seg
        and _state.text
        and now_ts < _state.until
    )
    # 若要用 overlay，仅在粘滞到期时切入，避免乱跳
    if sticky_alive:
        return _state.segment, _state.text

    if overlay and (force or random.random() < (0.45 if overlay.startswith("payday") else 0.28)):
        use_seg = overlay

    pool = POOLS.get(use_seg) or POOLS.get(seg) or ["上班计时中"]
    # 尽量不连抽同一句
    idx = random.randrange(len(pool))
    if len(pool) > 1 and idx == _state.last_idx and use_seg == _state.segment:
        idx = (idx + 1) % len(pool)
    text = pool[idx]
    hold = random.uniform(180.0, 480.0)  # 3–8 分钟
    # near_off / overtime 稍短一点，更有临场感
    if use_seg in ("near_off", "overtime", "pre_lunch"):
        hold = random.uniform(120.0, 300.0)
    _state.segment = use_seg
    _state.text = text
    _state.until = now_ts + hold
    _state.last_idx = idx
    return use_seg, text


def reset_phrases() -> None:
    global _state
    _state = _Sticky()
