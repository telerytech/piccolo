from __future__ import annotations

import typing as t

from piccolo.columns.base import Column
from piccolo.query.base import Query
from piccolo.querystring import QueryString

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.table import Table


class DropIndex(Query):
    def __init__(
        self,
        table: t.Type[Table],
        columns: t.List[t.Union[Column, str]],
        if_exists: bool = True,
    ):
        self.columns = columns
        self.if_exists = True
        super().__init__(table)

    @property
    def column_names(self) -> t.List[str]:
        return [
            i._meta.name if isinstance(i, Column) else i for i in self.columns
        ]

    @property
    def querystrings(self) -> t.Sequence[QueryString]:
        column_names = self.column_names
        index_name = self.table._get_index_name(column_names)
        query = "DROP INDEX"
        if self.if_exists:
            query += " IF EXISTS"
        return [QueryString(f"{query} {index_name}")]
