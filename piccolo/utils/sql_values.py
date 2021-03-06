from __future__ import annotations
from enum import Enum
import typing as t

from piccolo.utils.encoding import dump_json

if t.TYPE_CHECKING:
    from piccolo.columns import Column


def convert_to_sql_value(value: t.Any, column: Column) -> t.Any:
    """
    Some values which can be passed into Piccolo queries aren't valid in the
    database. For example, Enums, Table instances, and dictionaries for JSON
    columns.
    """
    from piccolo.table import Table
    from piccolo.columns.column_types import JSON, JSONB

    if isinstance(value, Table):
        return value.id
    elif isinstance(value, Enum):
        return value.value
    elif isinstance(column, (JSON, JSONB)) and not isinstance(value, str):
        return dump_json(value)
    else:
        return value
