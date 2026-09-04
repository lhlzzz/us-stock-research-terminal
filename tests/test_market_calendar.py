from __future__ import annotations

from datetime import date, datetime

from market_calendar import BEIJING_TZ, CALENDAR, closed_us_session_date, is_trading_day
from us_profit_ticket_pipeline import bday_date
from xiaomei_scheduler import closed_us_session_date as scheduler_closed_session


def test_monday_beijing_maps_to_friday_session():
    monday = datetime(2026, 9, 7, 5, tzinfo=BEIJING_TZ)
    assert closed_us_session_date(monday) == date(2026, 9, 4)
    assert is_trading_day(date(2026, 9, 4)) is True
    session = CALENDAR.pipeline_session(monday)
    assert session["target_session"] == "2026-09-04"
    assert session["actual_previous_trading_session"] == "2026-09-04"
    assert session["session_status"] == "COMPLETED"


def test_holiday_maps_to_previous_us_session():
    holiday = datetime(2026, 7, 4, 5, tzinfo=BEIJING_TZ)
    assert scheduler_closed_session(holiday) == date(2026, 7, 2)
    assert is_trading_day(date(2026, 7, 3)) is False


def test_forward_dates_use_us_market_calendar():
    assert bday_date(__import__("pandas").Timestamp("2026-07-02"), 1) == "2026-07-06"
