from __future__ import annotations

import datetime
import typing as t

from piccolo.columns.column_types import OnDelete, OnUpdate
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.table import Table


def deserialise_legacy_params(name: str, value: str) -> t.Any:
    """
    Earlier versions of Piccolo serialised parameters differently. This is
    here purely for backwards compatibility.
    """
    if name == "references":
        components = value.split("|")
        if len(components) == 1:
            class_name = components[0]
            tablename = None
        elif len(components) == 2:
            class_name, tablename = components
        else:
            raise ValueError(
                "Unrecognised Table serialisation - should either be "
                "`SomeClassName` or `SomeClassName|some_table_name`."
            )

        _Table: t.Type[Table] = type(
            class_name, (Table,), {},
        )
        if tablename:
            _Table._meta.tablename = tablename
        return _Table

    ###########################################################################

    if name == "on_delete":
        enum_name, item_name = value.split(".")
        if enum_name == "OnDelete":
            return getattr(OnDelete, item_name)

    ###########################################################################

    if name == "on_update":
        enum_name, item_name = value.split(".")
        if enum_name == "OnUpdate":
            return getattr(OnUpdate, item_name)

    ###########################################################################

    if name == "default":
        if value in ("TimestampDefault.now", "DatetimeDefault.now"):
            return TimestampNow()
        else:
            try:
                _value = datetime.datetime.fromisoformat(value)
            except ValueError:
                pass
            else:
                return _value

    return value
