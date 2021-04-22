from __future__ import annotations

import datetime
import typing as t

from .base import Default


class TimestampOffset(Default):
    def __init__(
        self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0
    ):
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds

    @property
    def postgres(self):
        interval_string = self.get_postgres_interval_string(
            ["days", "hours", "minutes", "seconds"]
        )
        return f"CURRENT_TIMESTAMP + INTERVAL '{interval_string}'"

    @property
    def sqlite(self):
        interval_string = self.get_sqlite_interval_string(
            ["days", "hours", "minutes", "seconds"]
        )
        return f"(datetime(CURRENT_TIMESTAMP, {interval_string}))"

    def python(self):
        return datetime.datetime.now() + datetime.timedelta(
            days=self.days,
            hours=self.hours,
            minutes=self.minutes,
            seconds=self.seconds,
        )


class TimestampNow(Default):
    @property
    def postgres(self):
        return "current_timestamp"

    @property
    def sqlite(self):
        return "current_timestamp"

    def python(self):
        return datetime.datetime.now()


class TimestampCustom(Default):
    def __init__(
        self,
        year: int = 2000,
        month: int = 1,
        day: int = 1,
        hour: int = 0,
        second: int = 0,
        microsecond: int = 0,
    ):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.second = second
        self.microsecond = microsecond

    @property
    def datetime(self):
        return datetime.datetime(
            year=self.year,
            month=self.month,
            day=self.day,
            hour=self.hour,
            second=self.second,
            microsecond=self.microsecond,
        )

    @property
    def postgres(self):
        return "'{}'".format(self.datetime.isoformat().replace("T", " "))

    @property
    def sqlite(self):
        return "'{}'".format(self.datetime.isoformat().replace("T", " "))

    def python(self):
        return self.datetime

    @classmethod
    def from_datetime(cls, instance: datetime.datetime):  # type: ignore
        return cls(
            year=instance.year,
            month=instance.month,
            day=instance.month,
            hour=instance.hour,
            second=instance.second,
            microsecond=instance.microsecond,
        )


###############################################################################
# For backwards compatibility:


class DatetimeDefault:
    now = TimestampNow()


###############################################################################

TimestampArg = t.Union[
    TimestampCustom,
    TimestampNow,
    TimestampOffset,
    None,
    datetime.datetime,
    DatetimeDefault,
]


__all__ = [
    "TimestampArg",
    "TimestampCustom",
    "TimestampNow",
    "TimestampOffset",
]
