from datetime import date

import pytest

from hr_assistant.employees import Employee, completed_years, leave_balance

TODAY = date(2026, 10, 15)


def employee(start: date, used: int = 0) -> Employee:
    return Employee(id="T1", name="Test", department="Test", start_date=start, used_leave_days=used)


def started_years_ago(years: int) -> date:
    return TODAY.replace(year=TODAY.year - years)


@pytest.mark.parametrize("start, today, expected", [
    (date(2020, 6, 15), date(2026, 6, 15), 6),   # anniversary counts as completed
    (date(2020, 6, 15), date(2026, 6, 14), 5),   # one day short
    (date(2026, 8, 1), date(2026, 10, 15), 0),
    (date(2027, 1, 1), date(2026, 10, 15), 0),   # future start date never goes negative
    (date(2020, 2, 29), date(2021, 2, 28), 0),   # leap day: year completes on 1 March
    (date(2020, 2, 29), date(2021, 3, 1), 1),
])
def test_completed_years(start, today, expected):
    assert completed_years(start, today) == expected


@pytest.mark.parametrize("years, days, section", [
    (1, 14, "5.7.4.1"),
    (5, 14, "5.7.4.1"),
    (6, 20, "5.7.4.2"),
    (15, 20, "5.7.4.2"),  # boundary as currently coded; verify against the regulation text
    (16, 24, "5.7.4.3"),
])
def test_entitlement_by_seniority(years, days, section):
    balance = leave_balance(employee(started_years_ago(years)), TODAY)
    assert balance.eligible
    assert (balance.years_of_service, balance.entitled_days, balance.rule_section) == (years, days, section)


def test_not_eligible_in_first_year():
    balance = leave_balance(employee(date(2026, 8, 1)), TODAY)
    assert not balance.eligible
    assert balance.entitled_days == 0
    assert balance.rule_section == "5.7.4"


def test_remaining_days():
    assert leave_balance(employee(started_years_ago(10), used=12), TODAY).remaining_days == 8


def test_remaining_days_never_negative():
    assert leave_balance(employee(started_years_ago(3), used=20), TODAY).remaining_days == 0
