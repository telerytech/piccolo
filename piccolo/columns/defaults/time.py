from __future__ import annotations

import datetime
import typing as t

from .base import Default


class TimeOffset(Default):
    def __init__(self, hours: int, minutes: int, seconds: int):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds

    @property
    def postgres(self):
        interval_string = self.get_postgres_interval_string(
            ["hours", "minutes", "seconds"]
        )
        return f"CURRENT_TIME + INTERVAL '{interval_string}'"

    @property
    def sqlite(self):
        interval_string = self.get_sqlite_interval_string(
            ["hours", "minutes", "seconds"]
        )
        return f"(time(CURRENT_TIME, {interval_string}))"

    def python(self):
        return (
            datetime.datetime.now()
            + datetime.timedelta(
                hours=self.hours, minutes=self.minutes, seconds=self.seconds
            )
        ).time


class TimeNow(Default):
    @property
    def postgres(self):
        return "CURRENT_TIME"

    @property
    def sqlite(self):
        return "CURRENT_TIME"

    def python(self):
        return datetime.datetime.now().time()


class TimeCustom(Default):
    def __init__(self, hour: int, minute: int, second: int):
        self.hour = hour
        self.minute = minute
        self.second = second
        self.time = datetime.time(hour=hour, minute=minute, second=second)

    @property
    def postgres(self):
        return self.time.isostring()

    @property
    def sqlite(self):
        return self.time.isostring()

    def python(self):
        return self.time

    @classmethod
    def from_time(cls, instance: datetime.time):
        return cls(
            hour=instance.hour, minute=instance.minute, second=instance.second
        )


TimeArg = t.Union[TimeCustom, TimeNow, TimeOffset, None, datetime.time]


__all__ = ["TimeArg", "TimeCustom", "TimeNow", "TimeOffset"]
