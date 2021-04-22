from __future__ import annotations

import datetime
import typing as t

from .base import Default


class DateOffset(Default):
    def __init__(self, days: int):
        self.days = days

    @property
    def postgres(self):
        interval_string = self.get_postgres_interval_string(["days"])
        return f"CURRENT_DATE + INTERVAL '{interval_string}'"

    @property
    def sqlite(self):
        interval_string = self.get_sqlite_interval_string(["days"])
        return f"(datetime(CURRENT_TIMESTAMP, {interval_string}))"

    def python(self):
        return (
            datetime.datetime.now() + datetime.timedelta(days=self.days)
        ).date


class DateNow(Default):
    @property
    def postgres(self):
        return "CURRENT_DATE"

    @property
    def sqlite(self):
        return "CURRENT_DATE"

    def python(self):
        return datetime.datetime.now().date()


class DateCustom(Default):
    def __init__(
        self, year: int, month: int, day: int,
    ):
        self.day = day
        self.month = month
        self.year = year
        self.date = datetime.date(year=year, month=month, day=day)

    @property
    def postgres(self):
        return self.date.isostring()

    @property
    def sqlite(self):
        return self.date.isostring()

    def python(self):
        return self.date

    @classmethod
    def from_date(cls, instance: datetime.date):
        return cls(
            year=instance.year, month=instance.month, day=instance.month
        )


# Might add an enum back which encapsulates all of the options.
DateArg = t.Union[DateOffset, DateCustom, DateNow, None, datetime.date]


__all__ = ["DateArg", "DateOffset", "DateCustom", "DateNow"]
