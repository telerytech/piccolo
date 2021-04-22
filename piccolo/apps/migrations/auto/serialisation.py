from __future__ import annotations

import datetime
import decimal
import inspect
import typing as t
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

from piccolo.columns.defaults.base import Default
from piccolo.columns.reference import LazyTableReference
from piccolo.table import Table

from .serialisation_legacy import deserialise_legacy_params

###############################################################################


@dataclass
class SerialisedClass:
    instance: object

    def __hash__(self):
        return self.instance.__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def _serialise_value(self, value):
        return f"'{value}'" if isinstance(value, str) else value

    def __repr__(self):
        args = ", ".join(
            [
                f"{key}={self._serialise_value(value)}"
                for key, value in self.instance.__dict__.items()
            ]
        )
        return f"{self.instance.__class__.__name__}({args})"


@dataclass
class SerialisedTableType:
    table_type: t.Type[Table]

    def __hash__(self):
        return hash(
            f"{self.table_type._meta.tablename}-{self.table_type.__name__}"
        )

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __repr__(self):
        tablename = self.table_type._meta.tablename
        class_name = self.table_type.__name__
        return f'class {class_name}(Table, tablename="{tablename}"): pass'

    def __lt__(self, other):
        return repr(self) < repr(other)


@dataclass
class SerialisedCallable:
    callable_: t.Callable

    def __hash__(self):
        return hash(self.callable_.__name__)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __repr__(self):
        return self.callable_.__name__


@dataclass
class SerialisedUUID:
    instance: uuid.UUID

    def __hash__(self):
        return self.instance.int

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __repr__(self):
        return f"UUID({str(self.instance)})"


###############################################################################


@dataclass
class Import:
    module: str
    target: str

    def __repr__(self):
        return f"from {self.module} import {self.target}"

    def __hash__(self):
        return hash(f"{self.module}-{self.target}")

    def __lt__(self, other):
        return repr(self) < repr(other)


@dataclass
class SerialisedParams:
    params: t.Dict[str, t.Any]
    extra_imports: t.List[Import]
    extra_definitions: t.List[str] = field(default_factory=list)


###############################################################################


def serialise_params(params: t.Dict[str, t.Any]) -> SerialisedParams:
    """
    When writing column params to a migration file, we need to serialise some
    of the values.
    """
    params = deepcopy(params)
    extra_imports: t.List[Import] = []
    extra_definitions: t.List[t.Any] = []

    for key, value in params.items():

        # Class instances
        if isinstance(value, Default):
            params[key] = SerialisedClass(instance=value)
            extra_imports.append(
                Import(
                    module=value.__class__.__module__,
                    target=value.__class__.__name__,
                )
            )
            continue

        # Dates and times
        if isinstance(
            value, (datetime.time, datetime.datetime, datetime.date)
        ):
            # Already has a good __repr__.
            extra_imports.append(
                Import(
                    module=value.__class__.__module__,
                    target=value.__class__.__name__,
                )
            )
            continue

        # UUIDs
        if isinstance(value, uuid.UUID):
            params[key] = SerialisedUUID(instance=value)
            extra_imports.append(Import(module="uuid", target="UUID"))
            continue

        # Decimals
        if isinstance(value, decimal.Decimal):
            # Already has a good __repr__.
            extra_imports.append(Import(module="decimal", target="Decimal"))
            continue

        # Enums
        if isinstance(value, Enum):
            # Enums already have a good __repr__.
            extra_imports.append(
                Import(
                    module=value.__module__, target=value.__class__.__name__,
                )
            )
            continue

        # Functions
        if inspect.isfunction(value):
            if value.__name__ == "<lambda>":
                raise ValueError("Lambdas can't be serialised")

            params[key] = SerialisedCallable(callable_=value)
            extra_imports.append(
                Import(module=value.__module__, target=value.__name__)
            )
            continue

        # Lazy imports - we need to resolve these now, in case the target
        # table class gets deleted in the future.
        if isinstance(value, LazyTableReference):
            table_type = value.resolve()
            params[key] = SerialisedCallable(callable_=table_type)
            extra_definitions.append(
                SerialisedTableType(table_type=table_type)
            )
            extra_imports.append(
                Import(module=Table.__module__, target="Table")
            )
            continue

        # Replace any Table class values into class and table names
        if inspect.isclass(value) and issubclass(value, Table):
            params[key] = SerialisedCallable(callable_=value)
            extra_definitions.append(SerialisedTableType(table_type=value))
            extra_imports.append(
                Import(module=Table.__module__, target="Table")
            )
            continue

        # All other types can remain as is.

    return SerialisedParams(
        params=params,
        extra_imports=[i for i in set(extra_imports)],
        extra_definitions=[i for i in set(extra_definitions)],
    )


def deserialise_params(params: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    """
    When reading column params from a migration file, we need to convert
    them from their serialised form.
    """
    params = deepcopy(params)

    for key, value in params.items():
        # This is purely for backwards compatibility.
        if isinstance(value, str) and not isinstance(value, Enum):
            if value != "self":
                params[key] = deserialise_legacy_params(name=key, value=value)
        elif isinstance(value, SerialisedClass):
            params[key] = value.instance
        elif isinstance(value, SerialisedUUID):
            params[key] = value.instance
        elif isinstance(value, SerialisedCallable):
            params[key] = value.callable_
        elif isinstance(value, SerialisedTableType):
            params[key] = value.table_type

    return params
