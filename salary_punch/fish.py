# -*- coding: utf-8 -*-
"""摸鱼状态：手动/进游戏自动；统计摸鱼时长与血赚（今日/本月/全部）。"""

from __future__ import annotations

from datetime import date, datetime

from .config import ConfigStore, now_local

VIEW_MODES = ("today", "month", "all")
VIEW_LABELS = {"today": "今日", "month": "本月", "all": "一共"}


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _month_key(d: date | None = None) -> str:
    d = d or date.today()
    return f"{d.year:04d}-{d.month:02d}"


def _compute_live(store: ConfigStore, hourly_rate: float, today_earned: float) -> tuple[float, float]:
    if not store.get("fishing"):
        return 0.0, 0.0
    started = _parse_iso(str(store.get("fish_started_at") or ""))
    live_sec = max(0.0, (now_local() - started).total_seconds()) if started else 0.0
    base = float(store.get("fish_session_base_earned") or 0.0)
    live_earn = max(0.0, float(today_earned) - base)
    if live_earn <= 0 and live_sec > 0:
        rate = float(store.get("fish_hourly_snapshot") or hourly_rate or 0)
        live_earn = (live_sec / 3600.0) * rate
    return live_sec, live_earn


def _migrate_totals(store: ConfigStore) -> None:
    """把旧版仅有今日累计的数据补进本月/全部（只在空时补一次）。"""
    today_sec = float(store.get("fish_seconds_today") or 0)
    today_earn = float(store.get("fish_earned_today") or 0)
    month_sec = float(store.get("fish_seconds_month") or 0)
    all_sec = float(store.get("fish_seconds_all") or 0)
    if today_sec > 0 and month_sec <= 0 and all_sec <= 0:
        store.update(
            fish_seconds_month=today_sec,
            fish_earned_month=today_earn,
            fish_seconds_all=today_sec,
            fish_earned_all=today_earn,
            fish_month=_month_key(),
            fish_day=str(store.get("fish_day") or date.today().isoformat()),
        )


def clear_fish_if_new_day(
    store: ConfigStore,
    hourly_rate: float = 0.0,
    today_earned: float = 0.0,
) -> None:
    """跨自然日清零今日；跨月清零本月；进行中会话先结算再续计。"""
    _migrate_totals(store)
    today = date.today().isoformat()
    month = _month_key()
    old_day = str(store.get("fish_day") or "")
    old_month = str(store.get("fish_month") or "")

    if not old_day and not old_month:
        store.update(fish_day=today, fish_month=month)
        return

    if old_day == today and (not old_month or old_month == month):
        if not old_month:
            store.update(fish_month=month)
        return

    live_sec, live_earn = _compute_live(store, hourly_rate, today_earned)
    fishing = bool(store.get("fishing"))

    # 进行中会话先计入旧日的今日/本月/全部
    sec_month = float(store.get("fish_seconds_month") or 0) + live_sec
    earn_month = float(store.get("fish_earned_month") or 0) + live_earn
    sec_all = float(store.get("fish_seconds_all") or 0) + live_sec
    earn_all = float(store.get("fish_earned_all") or 0) + live_earn

    # 跨月：本月从零开始（旧月数据已在 all 里）
    if old_month and old_month != month:
        sec_month = 0.0
        earn_month = 0.0

    updates: dict = {
        "fish_day": today,
        "fish_month": month,
        "fish_seconds_today": 0.0,
        "fish_earned_today": 0.0,
        "fish_seconds_month": sec_month,
        "fish_earned_month": earn_month,
        "fish_seconds_all": sec_all,
        "fish_earned_all": earn_all,
    }
    if fishing:
        updates.update(
            fish_started_at=now_local().isoformat(timespec="seconds"),
            fish_session_base_earned=float(today_earned),
        )
    store.update(**updates)


def is_fishing(store: ConfigStore) -> bool:
    # 跨日结算交给 fish_stats/start/stop（带时薪），避免无费率误结
    return bool(store.get("fishing"))


def is_manual_fish(store: ConfigStore) -> bool:
    return bool(store.get("fish_manual"))


def start_fish(
    store: ConfigStore,
    hourly_rate: float,
    today_earned: float,
    *,
    manual: bool = False,
) -> None:
    clear_fish_if_new_day(store, hourly_rate, today_earned)
    if store.get("fishing"):
        if manual and not store.get("fish_manual"):
            store.update(fish_manual=True)
        return
    store.update(
        fishing=True,
        fish_manual=bool(manual),
        fish_started_at=now_local().isoformat(timespec="seconds"),
        fish_session_base_earned=float(today_earned),
        fish_hourly_snapshot=float(hourly_rate),
        fish_day=date.today().isoformat(),
        fish_month=_month_key(),
    )


def stop_fish(store: ConfigStore, hourly_rate: float, today_earned: float) -> dict:
    clear_fish_if_new_day(store, hourly_rate, today_earned)
    if not store.get("fishing"):
        return {"seconds": 0.0, "earned": 0.0}
    live_sec, live_earn = _compute_live(store, hourly_rate, today_earned)
    store.update(
        fishing=False,
        fish_manual=False,
        fish_started_at="",
        fish_session_base_earned=0.0,
        fish_seconds_today=float(store.get("fish_seconds_today") or 0) + live_sec,
        fish_earned_today=float(store.get("fish_earned_today") or 0) + live_earn,
        fish_seconds_month=float(store.get("fish_seconds_month") or 0) + live_sec,
        fish_earned_month=float(store.get("fish_earned_month") or 0) + live_earn,
        fish_seconds_all=float(store.get("fish_seconds_all") or 0) + live_sec,
        fish_earned_all=float(store.get("fish_earned_all") or 0) + live_earn,
        fish_day=date.today().isoformat(),
        fish_month=_month_key(),
    )
    return {"seconds": live_sec, "earned": live_earn}


def toggle_fish(store: ConfigStore, hourly_rate: float, today_earned: float) -> bool:
    if is_fishing(store):
        stop_fish(store, hourly_rate, today_earned)
        return False
    start_fish(store, hourly_rate, today_earned, manual=True)
    return True


def ensure_auto_fish(store: ConfigStore, hourly_rate: float, today_earned: float) -> None:
    """进游戏/小应用：若未摸鱼则自动开（非手动）。"""
    start_fish(store, hourly_rate, today_earned, manual=False)


def end_auto_fish_if_needed(store: ConfigStore, hourly_rate: float, today_earned: float) -> None:
    """退出游戏回薪资：仅当本次非手动摸鱼时结束。"""
    if is_fishing(store) and not is_manual_fish(store):
        stop_fish(store, hourly_rate, today_earned)


def cycle_fish_view(store: ConfigStore) -> str:
    cur = str(store.get("fish_view") or "today")
    try:
        idx = VIEW_MODES.index(cur)
    except ValueError:
        idx = 0
    nxt = VIEW_MODES[(idx + 1) % len(VIEW_MODES)]
    store.update(fish_view=nxt)
    return nxt


def fish_view_mode(store: ConfigStore) -> str:
    mode = str(store.get("fish_view") or "today")
    return mode if mode in VIEW_MODES else "today"


def fish_stats(store: ConfigStore, hourly_rate: float, today_earned: float) -> dict:
    clear_fish_if_new_day(store, hourly_rate, today_earned)
    sec_done = float(store.get("fish_seconds_today") or 0)
    earn_done = float(store.get("fish_earned_today") or 0)
    month_done = float(store.get("fish_seconds_month") or 0)
    month_earn = float(store.get("fish_earned_month") or 0)
    all_done = float(store.get("fish_seconds_all") or 0)
    all_earn = float(store.get("fish_earned_all") or 0)
    live_sec, live_earn = _compute_live(store, hourly_rate, today_earned)
    return {
        "active": bool(store.get("fishing")),
        "manual": bool(store.get("fish_manual")),
        "session_seconds": live_sec,
        "session_earned": live_earn,
        "today_seconds": sec_done + live_sec,
        "today_earned": earn_done + live_earn,
        "month_seconds": month_done + live_sec,
        "month_earned": month_earn + live_earn,
        "all_seconds": all_done + live_sec,
        "all_earned": all_earn + live_earn,
        "view": fish_view_mode(store),
    }


def format_duration(seconds: float) -> str:
    s = int(max(0, seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}小时{m}分"
    if m:
        return f"{m}分{sec}秒"
    return f"{sec}秒"



def checkpoint_fish(store: ConfigStore, hourly_rate: float, today_earned: float) -> None:
    """进行中会话定期落盘：把 live 秒数并入今日/本月/一共，并重置本段起点。

    杀进程也能保住大部分时长；界面上的「进行中」会从 0 再累加。
    """
    clear_fish_if_new_day(store, hourly_rate, today_earned)
    if not store.get("fishing"):
        return
    live_sec, live_earn = _compute_live(store, hourly_rate, today_earned)
    if live_sec <= 0 and live_earn <= 0:
        return
    store.update(
        fish_seconds_today=float(store.get("fish_seconds_today") or 0) + live_sec,
        fish_earned_today=float(store.get("fish_earned_today") or 0) + live_earn,
        fish_seconds_month=float(store.get("fish_seconds_month") or 0) + live_sec,
        fish_earned_month=float(store.get("fish_earned_month") or 0) + live_earn,
        fish_seconds_all=float(store.get("fish_seconds_all") or 0) + live_sec,
        fish_earned_all=float(store.get("fish_earned_all") or 0) + live_earn,
        fish_started_at=now_local().isoformat(timespec="seconds"),
        fish_session_base_earned=float(today_earned),
        fish_day=date.today().isoformat(),
        fish_month=_month_key(),
    )


def settle_fish_on_exit(store: ConfigStore, hourly_rate: float, today_earned: float) -> None:
    """退出进程：无论手动/自动摸鱼都结算并关闭会话。"""
    if store.get("fishing"):
        stop_fish(store, hourly_rate, today_earned)
    else:
        # 确保已写盘
        try:
            store.save()
        except Exception:
            pass
