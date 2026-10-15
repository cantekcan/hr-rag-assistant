"""Employee records and annual leave calculation.

The employee file is synthetic demo data standing in for an HR system.
"""
import json
from dataclasses import dataclass
from datetime import date
from functools import cache

from hr_assistant import config


@dataclass(frozen=True)
class Employee:
    id: str
    name: str
    department: str
    start_date: date
    used_leave_days: int


@dataclass(frozen=True)
class LeaveBalance:
    employee_name: str
    start_date: str
    years_of_service: int
    eligible: bool
    entitled_days: int
    used_days: int
    remaining_days: int
    rule_section: str  # regulation section the entitlement comes from


# Annual leave by completed years of service, as written in regulation section 5.7.4.
# Each row: (max completed years, days per year, section). Leave is earned after the first full year.
LEAVE_RULES = [
    (5, 14, "5.7.4.1"),
    (15, 20, "5.7.4.2"),
    (None, 24, "5.7.4.3"),
]
ELIGIBILITY_SECTION = "5.7.4"


@cache
def _load() -> dict[str, Employee]:
    records = json.loads(config.EMPLOYEES_PATH.read_text(encoding="utf-8"))
    return {
        r["id"]: Employee(id=r["id"], name=r["name"], department=r["department"],
                          start_date=date.fromisoformat(r["start_date"]),
                          used_leave_days=r["used_leave_days"])
        for r in records
    }


def get_employee(employee_id: str) -> Employee | None:
    return _load().get(employee_id)


def list_employees() -> list[Employee]:
    return list(_load().values())


def completed_years(start: date, today: date) -> int:
    years = today.year - start.year
    if (today.month, today.day) < (start.month, start.day):
        years -= 1
    return max(years, 0)


def leave_balance(employee: Employee, today: date) -> LeaveBalance:
    years = completed_years(employee.start_date, today)
    if years < 1:
        entitled, section = 0, ELIGIBILITY_SECTION
    else:
        entitled, section = next((days, sec) for limit, days, sec in LEAVE_RULES
                                 if limit is None or years <= limit)
    return LeaveBalance(
        employee_name=employee.name,
        start_date=employee.start_date.isoformat(),
        years_of_service=years,
        eligible=years >= 1,
        entitled_days=entitled,
        used_days=employee.used_leave_days,
        remaining_days=max(entitled - employee.used_leave_days, 0),
        rule_section=section,
    )