from __future__ import annotations

import typing as t
from abc import ABCMeta, abstractmethod

from piccolo.utils.sync import run_sync
from piccolo.utils.warnings import Level, colored_warning

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.query.base import Query


class Batch:
    pass


class Engine(metaclass=ABCMeta):
    def __init__(self):
        run_sync(self.check_version())
        run_sync(self.prep_database())

    @property
    @abstractmethod
    def engine_type(self) -> str:
        pass

    @property
    @abstractmethod
    def min_version_number(self) -> float:
        pass

    @abstractmethod
    async def get_version(self) -> float:
        pass

    @abstractmethod
    async def prep_database(self):
        pass

    @abstractmethod
    async def batch(self, query: Query, batch_size: int = 100) -> Batch:
        pass

    async def check_version(self):
        """
        Warn if the database version isn't supported.
        """
        try:
            version_number = await self.get_version()
        except Exception as exception:
            colored_warning(
                f"Unable to fetch server version: {exception}",
                level=Level.high,
            )
            return

        engine_type = self.engine_type.capitalize()
        print(f"Running {engine_type} version {version_number}")
        if version_number < self.min_version_number:
            message = (
                f"This version of {self.engine_type} isn't supported "
                f"(< {self.min_version_number}) - some features might not be "
                "available. For instructions on installing databases, see the "
                "Piccolo docs."
            )
            colored_warning(message, stacklevel=3)
