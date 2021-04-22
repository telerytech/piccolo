from __future__ import annotations

import typing as t
from abc import ABC, abstractmethod, abstractproperty


class Default(ABC):
    @abstractproperty
    def postgres(self) -> str:
        pass

    @abstractproperty
    def sqlite(self) -> str:
        pass

    @abstractmethod
    def python(self):
        pass

    def get_postgres_interval_string(self, attributes: t.List[str]) -> str:
        """
        Returns a string usable as an interval argument in Postgres e.g.
        "1 day 2 hour".

        :arg attributes:
            Date / time attributes to extract from the instance. e.g.
            ['hours', 'minutes']
        """
        interval_components = []
        for attr_name in attributes:
            attr = getattr(self, attr_name, None)
            if attr is not None:
                interval_components.append(f"{attr} {attr_name}")

        return " ".join(interval_components)

    def get_sqlite_interval_string(self, attributes: t.List[str]) -> str:
        """
        Returns a string usable as an interval argument in SQLite e.g.
        "'-2 hours', '1 days'".

        :arg attributes:
            Date / time attributes to extract from the instance. e.g.
            ['hours', 'minutes']
        """
        interval_components = []
        for attr_name in attributes:
            attr = getattr(self, attr_name, None)
            if attr is not None:
                interval_components.append(f"'{attr} {attr_name}'")

        return ", ".join(interval_components)

    def __str__(self):
        args_str = ", ".join(
            [f"{key}={value}" for key, value in self.__dict__.items()]
        )
        return f"{self.__class__.__name__}({args_str})"

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash(self.__str__())


__all__ = ["Default"]
