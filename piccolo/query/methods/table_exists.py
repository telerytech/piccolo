from __future__ import annotations

import typing as t

from piccolo.query.base import Query
from piccolo.querystring import QueryString


class TableExists(Query):

    __slots__: t.Tuple = tuple()

    async def response_handler(self, response):
        return bool(response[0]["exists"])

    @property
    def sqlite_querystrings(self) -> t.Sequence[QueryString]:
        return [
            QueryString(
                "SELECT EXISTS(SELECT * FROM sqlite_master WHERE "
                f"name = '{self.table._meta.tablename}') AS 'exists'"
            )
        ]

    @property
    def postgres_querystrings(self) -> t.Sequence[QueryString]:
        return [
            QueryString(
                "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE "
                f"table_name = '{self.table._meta.tablename}')"
            )
        ]
