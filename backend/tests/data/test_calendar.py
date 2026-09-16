from datetime import date

from app.data.calendar import expected_business_dates


def test_bist_calendar_excludes_weekends_and_full_holidays():
    dates = expected_business_dates(date(2026, 4, 22), date(2026, 4, 24))

    assert dates == {date(2026, 4, 22), date(2026, 4, 24)}


def test_half_day_is_still_an_expected_business_date():
    dates = expected_business_dates(date(2026, 10, 28), date(2026, 10, 29))

    assert dates == {date(2026, 10, 28)}
