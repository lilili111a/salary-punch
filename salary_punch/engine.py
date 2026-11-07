# -*- coding: utf-8 -*-
"""薪资实时计算引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from .config import ConfigStore, hhmm_to_minutes, now_local
from .phrases import pick_phrase, resolve_segment
from ._period import attendance_in_range, pay_period_bounds
from .fish import fish_stats, is_fishing


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def scheduled_minutes(cfg: ConfigStore) -> int:
    start = hhmm_to_minutes(cfg.get("work_start", "09:00"))
    end = hhmm_to_minutes(cfg.get("work_end", "18:00"))
    total = max(0, end - start)
    if cfg.get("deduct_lunch", True):
        ls = hhmm_to_minutes(cfg.get("lunch_start", "12:00"))
        le = hhmm_to_minutes(cfg.get("lunch_end", "13:00"))
        lunch = max(0, le - ls)
        # only deduct lunch overlapping work window
        overlap = max(0, min(end, le) - max(start, ls))
        total = max(0, total - overlap)
        _ = lunch
    return total


def worked_seconds_in_window(
    now: datetime,
    work_start: str,
    work_end: str,
    lunch_start: str,
    lunch_end: str,
    deduct_lunch: bool,
    clock_in: str | None = None,
    clock_out: str | None = None,
) -> float:
    """今日在标准工时（或打卡区间）内已工作秒数，扣除午休。"""
    day = now.date()
    std_start = hhmm_to_minutes(work_start)
    std_end = hhmm_to_minutes(work_end)
    ls = hhmm_to_minutes(lunch_start)
    le = hhmm_to_minutes(lunch_end)

    # 早到按标准上班起算；晚到按打卡起算
    if clock_in:
        punch_in = hhmm_to_minutes(clock_in)
        ws = max(std_start, punch_in)
    else:
        ws = std_start
    if clock_out:
        we = hhmm_to_minutes(clock_out)
    else:
        we = std_end

    start_dt = datetime.combine(day, datetime.min.time()) + timedelta(minutes=ws)
    end_dt = datetime.combine(day, datetime.min.time()) + timedelta(minutes=we)

    if now < start_dt:
        return 0.0
    effective_end = min(now, end_dt)
    if clock_out:
        # day finished at clock_out
        effective_end = min(effective_end, end_dt)

    raw = (effective_end - start_dt).total_seconds()
    if raw <= 0:
        return 0.0

    if deduct_lunch:
        lunch_s = datetime.combine(day, datetime.min.time()) + timedelta(minutes=ls)
        lunch_e = datetime.combine(day, datetime.min.time()) + timedelta(minutes=le)
        overlap = max(
            0.0,
            (min(effective_end, lunch_e) - max(start_dt, lunch_s)).total_seconds(),
        )
        raw = max(0.0, raw - overlap)
    return raw


@dataclass
class Snapshot:
    now: datetime
    is_workday: bool
    is_paused: bool
    is_before_work: bool
    is_after_work: bool
    is_on_lunch: bool
    status_text: str
    today_earned: float
    month_earned: float  # 兼容旧字段名 = 本周期已到手
    month_estimate: float  # 本周期预估到手
    days_worked: int
    days_planned: int
    today_progress: float  # 0..1
    month_progress: float  # 0..1 vs estimate
    hourly_rate: float
    daily_rate: float
    seconds_worked_today: float
    scheduled_seconds: float
    payday_countdown: int
    period_start: str = ""  # 上一发薪日 ISO
    period_end: str = ""  # 下一发薪日 ISO
    fish_active: bool = False
    fish_session_seconds: float = 0.0
    fish_session_earned: float = 0.0
    fish_today_seconds: float = 0.0
    fish_today_earned: float = 0.0
    fish_month_seconds: float = 0.0
    fish_month_earned: float = 0.0
    fish_all_seconds: float = 0.0
    fish_all_earned: float = 0.0
    fish_view: str = "today"
    currency: str = "¥"


class SalaryEngine:
    def __init__(self, store: ConfigStore):
        self.store = store

    def rates(self, today: date | None = None) -> tuple[float, float, float, list[str], date, date]:
        """返回 (时薪, 日薪, 周期薪资基准, 周期出勤日, 上发薪日, 下发薪日)。

        月薪按「发薪周期」内出勤日均摊（税后到手）。
        """
        cfg = self.store
        today = today or date.today()
        last_pay, next_pay = pay_period_bounds(today, int(cfg.get("payday") or 10))
        days = attendance_in_range(self.store, last_pay, next_pay)
        n_days = max(1, len(days))
        mode = cfg.get("salary_mode", "monthly")
        sched_min = scheduled_minutes(cfg) or (8 * 60)
        sched_h = sched_min / 60.0

        if mode == "hourly":
            hourly = float(cfg.get("hourly_salary") or 0)
            daily = hourly * sched_h
            monthly = daily * n_days
        elif mode == "daily":
            daily = float(cfg.get("daily_salary") or 0)
            hourly = daily / sched_h if sched_h else 0
            monthly = daily * n_days
        else:
            monthly = float(cfg.get("monthly_salary") or 0)
            daily = monthly / n_days
            hourly = daily / sched_h if sched_h else 0
        return hourly, daily, monthly, days, last_pay, next_pay

    def snapshot(self, now: datetime | None = None) -> Snapshot:
        self.store.clear_pause_if_stale()
        now = now or now_local()
        today = now.date()
        cfg = self.store

        hourly, daily, monthly_base, planned, last_pay, next_pay = self.rates(today)
        planned_set = set(planned)
        # 是否上班仍看「自然日出勤日历」（本月勾选），与周期累计分开
        cal_days = set(self.store.month_attendance(today.year, today.month))
        is_workday = today.isoformat() in cal_days

        # 周期内已完成的全勤日（上一发薪日之后、今天之前）
        past_days = [d for d in planned if d < today.isoformat()]
        days_full = len(past_days)

        # punch-aware window selection
        punch = self.store.punch_today()
        paused = bool(cfg.get("paused_today")) and cfg.get("paused_date") == today.isoformat()

        auto = bool(cfg.get("auto_schedule", True))
        punch_mode = str(punch.get("mode") or "strict")
        planned_end = punch.get("planned_end")
        custom_hours = punch.get("custom_hours")

        win_start = str(cfg.get("work_start", "09:00"))
        win_end = str(cfg.get("work_end", "18:00"))
        clock_in = punch.get("in") if (not auto or punch.get("in")) else None
        clock_out = punch.get("out")

        if punch.get("in") and punch_mode == "custom":
            win_start = str(punch.get("in"))
            win_end = str(planned_end or win_end)
            clock_in = str(punch.get("in"))
            try:
                sched_sec = float(custom_hours) * 3600.0 if custom_hours is not None else scheduled_minutes(cfg) * 60.0
            except (TypeError, ValueError):
                sched_sec = scheduled_minutes(cfg) * 60.0
        else:
            sched_sec = scheduled_minutes(cfg) * 60.0

        if not auto and is_workday and not punch.get("in"):
            sec = 0.0
        elif not is_workday:
            sec = 0.0
        else:
            sec = worked_seconds_in_window(
                now,
                win_start,
                win_end,
                cfg.get("lunch_start", "12:00"),
                cfg.get("lunch_end", "13:00"),
                bool(cfg.get("deduct_lunch", True)),
                clock_in,
                clock_out,
            )

        # overtime beyond schedule at overtime_rate
        ot_rate = float(cfg.get("overtime_rate") or 1.5)
        base_sec = min(sec, sched_sec)
        ot_sec = max(0.0, sec - sched_sec)
        today_earned = (base_sec / 3600.0) * hourly + (ot_sec / 3600.0) * hourly * ot_rate

        # if day complete (after work or clocked out), cap at least to progress
        end_for_status = win_end
        if punch.get("in") and punch_mode == "custom" and planned_end:
            end_for_status = str(planned_end)
        if punch.get("in") and punch_mode != "custom":
            ws = max(hhmm_to_minutes(cfg.get("work_start", "09:00")), hhmm_to_minutes(str(punch.get("in"))))
        else:
            ws = hhmm_to_minutes(win_start if punch.get("in") else cfg.get("work_start", "09:00"))
        we = hhmm_to_minutes(end_for_status)
        ls = hhmm_to_minutes(cfg.get("lunch_start", "12:00"))
        le = hhmm_to_minutes(cfg.get("lunch_end", "13:00"))
        now_m = now.hour * 60 + now.minute + now.second / 60.0
        is_before = is_workday and now_m < ws
        is_after = is_workday and (bool(clock_out) or now_m >= we)
        is_lunch = (
            is_workday
            and bool(cfg.get("deduct_lunch", True))
            and ls <= now_m < le
            and not is_before
            and not is_after
        )

        today_progress = _clip(sec / sched_sec, 0.0, 1.0) if sched_sec else 0.0

        # days worked: past full + today if any progress
        days_worked = days_full
        if is_workday and (sec > 0 or is_after):
            # count today as partial day visually but "上了多少天班" usually means attended
            if sec > 60 or is_after or punch.get("in"):
                days_worked = days_full + 1

        # 今日若在周期出勤列表内才计入周期（发薪日当天通常开启下周期，今日不计入上周期）
        today_in_period = today.isoformat() in planned_set
        if is_workday and today_in_period and (sec > 60 or is_after or punch.get("in")):
            days_worked = days_full + 1
        period_earned = days_full * daily + (today_earned if (is_workday and today_in_period) else 0.0)
        future_days = [d for d in planned if d > today.isoformat()]
        if is_workday and today_in_period and not is_after:
            remain_today = max(0.0, daily - today_earned)
            period_estimate = period_earned + remain_today + len(future_days) * daily
        else:
            period_estimate = period_earned + len(future_days) * daily

        month_earned = period_earned
        month_estimate = period_estimate
        month_progress = _clip(month_earned / month_estimate, 0.0, 1.0) if month_estimate else 0.0

        countdown = (next_pay - today).days

        fishing = is_fishing(self.store)
        fs = fish_stats(self.store, hourly, today_earned)
        seg = resolve_segment(
            now=now,
            is_workday=is_workday,
            is_paused=paused,
            auto=auto,
            has_in=bool(punch.get("in")),
            work_start=str(cfg.get("work_start", "09:00")),
            work_end=str(cfg.get("work_end", "18:00")),
            lunch_start=str(cfg.get("lunch_start", "12:00")),
            lunch_end=str(cfg.get("lunch_end", "13:00")),
            deduct_lunch=bool(cfg.get("deduct_lunch", True)),
            clock_out=bool(clock_out),
            day_done=bool(is_after),
            is_fishing=bool(fishing),
        )
        _, status = pick_phrase(
            seg,
            payday_countdown=countdown,
            today_progress=today_progress,
            today_earned=today_earned,
            daily_rate=daily,
        )

        return Snapshot(
            now=now,
            is_workday=is_workday,
            is_paused=paused,
            is_before_work=is_before,
            is_after_work=is_after,
            is_on_lunch=is_lunch,
            status_text=status,
            today_earned=today_earned,
            month_earned=month_earned,
            month_estimate=month_estimate,
            days_worked=days_worked,
            days_planned=len(planned),
            today_progress=today_progress,
            month_progress=month_progress,
            hourly_rate=hourly,
            daily_rate=daily,
            seconds_worked_today=sec,
            scheduled_seconds=sched_sec,
            payday_countdown=countdown,
            period_start=last_pay.isoformat(),
            period_end=next_pay.isoformat(),
            fish_active=bool(fs["active"]),
            fish_session_seconds=float(fs["session_seconds"]),
            fish_session_earned=float(fs["session_earned"]),
            fish_today_seconds=float(fs["today_seconds"]),
            fish_today_earned=float(fs["today_earned"]),
            fish_month_seconds=float(fs["month_seconds"]),
            fish_month_earned=float(fs["month_earned"]),
            fish_all_seconds=float(fs["all_seconds"]),
            fish_all_earned=float(fs["all_earned"]),
            fish_view=str(fs.get("view") or "today"),
        )


def _last_day(year: int, month: int) -> int:
    import calendar

    return calendar.monthrange(year, month)[1]



def format_money(v: float, currency: str = "¥") -> str:
    return f"{currency}{v:,.2f}"
