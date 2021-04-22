from __future__ import annotations

import typing as t
from dataclasses import dataclass

from piccolo.query.base import Query
from piccolo.querystring import QueryString

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.table import Table


@dataclass
class Raw(Query):
    __slots__ = ("querystring",)

    def __init__(
        self, table: t.Type[Table], querystring: QueryString = QueryString("")
    ):
        super().__init__(table)
        self.querystring = querystring

    @property
    def querystrings(self) -> t.Sequence[QueryString]:
        return [self.querystring]
