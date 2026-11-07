# -*- coding: utf-8 -*-
"""配置与出勤持久化（本地 JSON）。"""

from __future__ import annotations

import calendar
import copy
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "salary_mode": "monthly",  # monthly | daily | hourly
    "monthly_salary": 15000.0,  # 税后到手月薪
    "net_pay": True,  # True=按税后/到手计，界面标注「到手」

    "daily_salary": 0.0,
    "hourly_salary": 0.0,
    "work_start": "09:00",
    "work_end": "18:00",
    "lunch_start": "12:00",
    "lunch_end": "13:00",
    "deduct_lunch": True,
    "timezone": "Asia/Shanghai",
    "payday": 10,
    "overtime_rate": 1.5,
    "weekend_is_workday": False,
    "auto_schedule": True,
    "autostart": True,
    "autostart_prompted": False,
    "always_on_top": True,
    "alpha": 0.95,
    "paused_today": False,
    "paused_date": "",
    "fishing": False,
    "fish_manual": False,
    "fish_started_at": "",
    "fish_session_base_earned": 0.0,
    "fish_hourly_snapshot": 0.0,
    "fish_seconds_today": 0.0,
    "fish_earned_today": 0.0,
    "fish_day": "",
    "fish_month": "",
    "fish_seconds_month": 0.0,
    "fish_earned_month": 0.0,
    "fish_seconds_all": 0.0,
    "fish_earned_all": 0.0,
    "fish_view": "today",  # today | month | all
    "ad_camouflage": True,  # 鼠标离开卡片时伪装成广告卡
    "ad_camouflage_delay_ms": 450,
    "ad_title": "企业效率套件 · 限时推广",
    "ad_subtitle": "协同办公 · 文档·日程一站提效",
    "ad_footer": "广告",
    "attendance": {},  # "YYYY-MM": ["YYYY-MM-DD", ...]
    "punches": {},  # "YYYY-MM-DD": {"in": "HH:MM", "out": "HH:MM"|null}
}


def _month_key(d: date | None = None) -> str:
    d = d or date.today()
    return f"{d.year:04d}-{d.month:02d}"


def weekday_dates(year: int, month: int, include_weekend: bool = False) -> list[str]:
    """生成本月默认出勤日。"""
    days: list[str] = []
    _, last = calendar.monthrange(year, month)
    for day in range(1, last + 1):
        d = date(year, month, day)
        if include_weekend or d.weekday() < 5:
            days.append(d.isoformat())
    return days


class ConfigStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()
        self.ensure_month_attendance()

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                merged = copy.deepcopy(DEFAULTS)
                merged.update(raw)
                # nested defaults
                if not isinstance(merged.get("attendance"), dict):
                    merged["attendance"] = {}
                if not isinstance(merged.get("punches"), dict):
                    merged["punches"] = {}
                self.data = merged
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self.data = copy.deepcopy(DEFAULTS)

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            self.data[k] = v
        self.save()

    def ensure_month_attendance(self, d: date | None = None) -> None:
        d = d or date.today()
        key = _month_key(d)
        att = self.data.setdefault("attendance", {})
        if key not in att or not isinstance(att.get(key), list) or not att[key]:
            att[key] = weekday_dates(
                d.year, d.month, bool(self.data.get("weekend_is_workday"))
            )
            self.save()

    def month_attendance(self, year: int | None = None, month: int | None = None) -> list[str]:
        today = date.today()
        year = year or today.year
        month = month or today.month
        key = f"{year:04d}-{month:02d}"
        att = self.data.setdefault("attendance", {})
        if key not in att:
            att[key] = weekday_dates(
                year, month, bool(self.data.get("weekend_is_workday"))
            )
            self.save()
        return list(att.get(key) or [])

    def set_month_attendance(self, year: int, month: int, days: list[str]) -> None:
        key = f"{year:04d}-{month:02d}"
        self.data.setdefault("attendance", {})[key] = sorted(set(days))
        self.save()

    def is_workday(self, d: date | None = None) -> bool:
        d = d or date.today()
        return d.isoformat() in self.month_attendance(d.year, d.month)

    def punch_today(self) -> dict[str, Any]:
        key = date.today().isoformat()
        punches = self.data.setdefault("punches", {})
        return dict(punches.get(key) or {})

    def set_punch(self, day: str, clock_in: str | None = None, clock_out: str | None = None, **extra) -> None:
        punches = self.data.setdefault("punches", {})
        cur = dict(punches.get(day) or {})
        if clock_in is not None:
            cur["in"] = clock_in
        if clock_out is not None:
            cur["out"] = clock_out
        for k, v in extra.items():
            if v is None and k in cur:
                cur.pop(k, None)
            elif v is not None:
                cur[k] = v
        punches[day] = cur
        self.save()

    def replace_punch(self, day: str, payload: dict) -> None:
        punches = self.data.setdefault("punches", {})
        punches[day] = dict(payload or {})
        self.save()

    def clear_pause_if_stale(self) -> None:
        today = date.today().isoformat()
        if self.data.get("paused_date") != today:
            self.data["paused_today"] = False
            self.data["paused_date"] = today
            self.save()


def parse_hhmm(s: str) -> tuple[int, int]:
    parts = (s or "00:00").strip().split(":")
    h = int(parts[0]) if parts else 0
    m = int(parts[1]) if len(parts) > 1 else 0
    return h, m


def hhmm_to_minutes(s: str) -> int:
    h, m = parse_hhmm(s)
    return h * 60 + m


def now_local() -> datetime:
    # 机器时区已是 Asia/Shanghai；直接用本地时间
    return datetime.now()
