from __future__ import annotations

import datetime
import typing as t

from .base import Default


class IntervalCustom(Default):  # lgtm [py/missing-equals]
    def __init__(
        self,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        milliseconds: int = 0,
        microseconds: int = 0,
    ):
        self.weeks = weeks
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        self.milliseconds = milliseconds
        self.microseconds = microseconds

    @property
    def timedelta(self):
        return datetime.timedelta(
            weeks=self.weeks,
            days=self.days,
            hours=self.hours,
            minutes=self.minutes,
            seconds=self.seconds,
            milliseconds=self.milliseconds,
            microseconds=self.microseconds,
        )

    @property
    def postgres(self):
        value = self.get_postgres_interval_string(
            attributes=[
                "weeks",
                "days",
                "hours",
                "minutes",
                "seconds",
                "milliseconds",
                "microseconds",
            ]
        )
        return f"'{value}'"

    @property
    def sqlite(self):
        return self.timedelta.total_seconds()

    def python(self):
        return self.timedelta

    @classmethod
    def from_timedelta(cls, instance: datetime.timedelta):
        return cls(
            days=instance.days,
            seconds=instance.seconds,
            microseconds=instance.microseconds,
        )


###############################################################################

IntervalArg = t.Union[
    IntervalCustom, None, datetime.timedelta,
]


__all__ = [
    "IntervalArg",
    "IntervalCustom",
]
