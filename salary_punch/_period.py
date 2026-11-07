# -*- coding: utf-8 -*-
"""发薪周期：上一发薪日 → 下一发薪日。"""

from __future__ import annotations

from datetime import date, timedelta


def _clamp_payday(year: int, month: int, payday: int) -> date:
    import calendar

    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(1, payday), last))


def pay_period_bounds(today: date, payday: int) -> tuple[date, date]:
    """返回 (上一发薪日, 下一发薪日)。

    周期口径：上一发薪日之后（不含发薪日当天）到下一发薪日（含）——
    即工作归属「下一张工资单」。若今天正好是发薪日，上一发薪日=今天，下一=下月发薪日，
    本周期已赚从明天起算（今天发的是上周期的钱）。
    """
    payday = int(payday or 10)
    this_pay = _clamp_payday(today.year, today.month, payday)
    if today < this_pay:
        # 下一发薪日=本月；上一=上月
        next_pay = this_pay
        y, m = today.year, today.month - 1
        if m < 1:
            y, m = y - 1, 12
        last_pay = _clamp_payday(y, m, payday)
    elif today == this_pay:
        last_pay = this_pay
        y, m = today.year, today.month + 1
        if m > 12:
            y, m = y + 1, 1
        next_pay = _clamp_payday(y, m, payday)
    else:
        last_pay = this_pay
        y, m = today.year, today.month + 1
        if m > 12:
            y, m = y + 1, 1
        next_pay = _clamp_payday(y, m, payday)
    return last_pay, next_pay


def iter_months(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def attendance_in_range(store, start_exclusive: date, end_inclusive: date) -> list[str]:
    """出勤日：start_exclusive < day <= end_inclusive。"""
    days: list[str] = []
    begin = start_exclusive + timedelta(days=1)
    if begin > end_inclusive:
        return []
    for y, m in iter_months(begin, end_inclusive):
        for iso in store.month_attendance(y, m):
            d = date.fromisoformat(iso)
            if begin <= d <= end_inclusive:
                days.append(iso)
    return sorted(days)
