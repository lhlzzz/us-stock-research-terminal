"""Canonical US equity market calendar.

Owner: USMarketCalendar. Other modules import from here instead of
hardcoding holiday lists or weekend skips.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BEIJING_TZ = ZoneInfo("Asia/Shanghai")

REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
PREMARKET_OPEN = time(4, 0)
AFTER_HOURS_CLOSE = time(20, 0)
EARLY_CLOSE = time(13, 0)

SESSION_REGULAR = "REGULAR"
SESSION_PREMARKET = "PRE_MARKET"
SESSION_AFTER_HOURS = "AFTER_HOURS"
SESSION_CLOSED = "CLOSED"


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    cursor = date(year, month, 1)
    while cursor.weekday() != weekday:
        cursor += timedelta(days=1)
    return cursor + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        cursor = date(year, 12, 31)
    else:
        cursor = date(year, month + 1, 1) - timedelta(days=1)
    while cursor.weekday() != weekday:
        cursor -= timedelta(days=1)
    return cursor


def _observed(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _easter(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = ((h + ll - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def nyse_holidays(year: int) -> set[date]:
    good_friday = _easter(year) - timedelta(days=2)
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    return {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),
        _nth_weekday(year, 2, 0, 3),
        good_friday,
        _last_weekday(year, 5, 0),
        _observed(date(year, 6, 19)),
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),
        thanksgiving,
        _observed(date(year, 12, 25)),
    }


def nyse_early_closes(year: int) -> set[date]:
    independence = date(year, 7, 4)
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    christmas = date(year, 12, 25)
    days: set[date] = {thanksgiving + timedelta(days=1)}
    eve = independence - timedelta(days=1)
    if eve.weekday() < 5 and eve not in nyse_holidays(year):
        days.add(eve)
    christmas_eve = christmas - timedelta(days=1)
    if christmas_eve.weekday() < 5 and christmas_eve not in nyse_holidays(year):
        days.add(christmas_eve)
    return days


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


class USMarketCalendar:
    """Single owner for US regular sessions, holidays, and clock windows."""

    timezone = ET

    def holidays(self, year: int) -> set[date]:
        return nyse_holidays(year)

    def early_closes(self, year: int) -> set[date]:
        return nyse_early_closes(year)

    def is_weekend(self, session_date: date | datetime | str) -> bool:
        return _as_date(session_date).weekday() >= 5

    def is_full_holiday(self, session_date: date | datetime | str) -> bool:
        day = _as_date(session_date)
        return day in nyse_holidays(day.year)

    def is_early_close(self, session_date: date | datetime | str) -> bool:
        day = _as_date(session_date)
        return day in nyse_early_closes(day.year)

    def is_trading_day(self, session_date: date | datetime | str | None = None) -> bool:
        day = _as_date(session_date) if session_date is not None else datetime.now(ET).date()
        if self.is_weekend(day):
            return False
        return not self.is_full_holiday(day)

    def session_close_time(self, session_date: date | datetime | str) -> time:
        day = _as_date(session_date)
        return EARLY_CLOSE if self.is_early_close(day) else REGULAR_CLOSE

    def session_open_time(self, session_date: date | datetime | str | None = None) -> time:
        return REGULAR_OPEN

    def next_trading_day(self, session_date: date | datetime | str) -> date:
        day = _as_date(session_date) + timedelta(days=1)
        while not self.is_trading_day(day):
            day += timedelta(days=1)
        return day

    def prev_trading_day(self, session_date: date | datetime | str) -> date:
        day = _as_date(session_date) - timedelta(days=1)
        while not self.is_trading_day(day):
            day -= timedelta(days=1)
        return day

    def add_trading_days(self, session_date: date | datetime | str, n: int) -> date:
        day = _as_date(session_date)
        if n >= 0:
            for _ in range(n):
                day = self.next_trading_day(day)
            return day
        for _ in range(-n):
            day = self.prev_trading_day(day)
        return day

    def latest_trading_day(self, ref_date: date | datetime | str | None = None) -> date:
        day = _as_date(ref_date) if ref_date is not None else datetime.now(ET).date()
        while not self.is_trading_day(day):
            day -= timedelta(days=1)
        return day

    def session_kind(self, now: datetime | None = None) -> str:
        current = (now or datetime.now(ET)).astimezone(ET)
        day = current.date()
        clock = current.timetz().replace(tzinfo=None)
        if not self.is_trading_day(day):
            return SESSION_CLOSED
        close = self.session_close_time(day)
        if PREMARKET_OPEN <= clock < REGULAR_OPEN:
            return SESSION_PREMARKET
        if REGULAR_OPEN <= clock < close:
            return SESSION_REGULAR
        if close <= clock < AFTER_HOURS_CLOSE:
            return SESSION_AFTER_HOURS
        return SESSION_CLOSED

    def is_regular_session(self, now: datetime | None = None) -> bool:
        return self.session_kind(now) == SESSION_REGULAR

    def session_completed(self, session_date: date | datetime | str, now: datetime | None = None) -> bool:
        day = _as_date(session_date)
        if not self.is_trading_day(day):
            return False
        current = (now or datetime.now(ET)).astimezone(ET)
        close_at = datetime.combine(day, self.session_close_time(day), tzinfo=ET)
        return current >= close_at

    def previous_completed_session(self, now: datetime | None = None) -> date:
        """Last US session that has already closed. Monday 05:00 BJT → Friday."""
        current = (now or datetime.now(ET)).astimezone(ET)
        day = current.date()
        if self.is_trading_day(day) and current.timetz().replace(tzinfo=None) >= self.session_close_time(day):
            return day
        return self.prev_trading_day(day)

    def quote_session_stamp(self, now: datetime | None = None) -> dict[str, Any]:
        """Session labels for a realtime quote. latest_price belongs to quote_session."""
        current = (now or datetime.now(ET)).astimezone(ET)
        day = current.date()
        if self.is_trading_day(day):
            session = day
        else:
            session = self.previous_completed_session(current)
        completed = self.session_completed(session, current) if self.is_trading_day(session) else True
        return {
            "session_date": session.isoformat(),
            "quote_session": session.isoformat(),
            "prev_close_session": self.prev_trading_day(session).isoformat(),
            "session_status": self.session_kind(current),
            "session_completed": completed,
            "bar_type": "DAILY_COMPLETE" if completed else "SNAPSHOT",
            "is_complete": completed,
        }

    def pipeline_session(self, now: datetime | None = None) -> dict[str, Any]:
        current = (now or datetime.now(BEIJING_TZ)).astimezone(BEIJING_TZ)
        target = self.previous_completed_session(current)
        return {
            "execution_time_bjt": current.isoformat(),
            "pipeline_execution_time": current.isoformat(),
            "target_session": target.isoformat(),
            "target_session_date": target.isoformat(),
            "actual_previous_trading_session": target.isoformat(),
            "session_status": "COMPLETED",
            "timezone": "America/New_York",
        }


CALENDAR = USMarketCalendar()
US_HOLIDAYS = {day for year in range(2024, 2031) for day in nyse_holidays(year)}


def is_trading_day(session_date: date | datetime | str | None = None) -> bool:
    return CALENDAR.is_trading_day(session_date)


def next_trading_day(session_date: date | datetime | str) -> date:
    return CALENDAR.next_trading_day(session_date)


def prev_trading_day(session_date: date | datetime | str) -> date:
    return CALENDAR.prev_trading_day(session_date)


def add_trading_days(session_date: date | datetime | str, n: int) -> date:
    return CALENDAR.add_trading_days(session_date, n)


def latest_us_trading_day(ref_date: date | datetime | str | None = None) -> date:
    return CALENDAR.latest_trading_day(ref_date)


def closed_us_session_date(now: datetime | None = None) -> date:
    return CALENDAR.previous_completed_session(now)


def is_us_regular_session(now: datetime | None = None) -> bool:
    return CALENDAR.is_regular_session(now)


def previous_completed_session(now: datetime | None = None) -> date:
    return CALENDAR.previous_completed_session(now)


if __name__ == "__main__":
    now = datetime.now(BEIJING_TZ)
    session = CALENDAR.pipeline_session(now)
    print("calendar_owner=scripts/market_calendar.py")
    print("now_bjt", now.isoformat())
    print("target_session", session.get("target_session"))
    print("previous_completed_session", CALENDAR.previous_completed_session(now).isoformat())
    print("is_trading_day", CALENDAR.is_trading_day(CALENDAR.previous_completed_session(now)))
