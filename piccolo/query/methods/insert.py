from __future__ import annotations

import typing as t
from dataclasses import dataclass

from piccolo.query.base import Query
from piccolo.query.mixins import AddDelegate
from piccolo.querystring import QueryString

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.table import Table


@dataclass
class Insert(Query):
    __slots__ = ("add_delegate",)

    def __init__(self, table: t.Type[Table], *instances: Table):
        super().__init__(table)
        self.add_delegate = AddDelegate()
        self.add(*instances)

    def add(self, *instances: Table) -> Insert:
        self.add_delegate.add(*instances, table_class=self.table)
        return self

    def run_callback(self, results):
        """
        Assign the ids of the created rows to the model instances.
        """
        for index, row in enumerate(results):
            self.add_delegate._add[index].id = row["id"]

    async def run_pre_functions(self):
        for function in self.table._meta.pre_insert:
            function()

    async def run_post_functions(self):
        for function in self.table._meta.post_insert:
            function()

    def run_pre_functions_sync(self):
        for function in self.table._meta.pre_insert:
            function()

    def run_post_functions_sync(self):
        for function in self.table._meta.post_insert:
            function()

    @property
    def sqlite_querystrings(self) -> t.Sequence[QueryString]:
        base = f"INSERT INTO {self.table._meta.tablename}"
        columns = ",".join([i._meta.name for i in self.table._meta.columns])
        values = ",".join(["{}" for i in self.add_delegate._add])
        query = f"{base} ({columns}) VALUES {values}"
        return [
            QueryString(
                query,
                *[i.querystring for i in self.add_delegate._add],
                query_type="insert",
            )
        ]

    @property
    def postgres_querystrings(self) -> t.Sequence[QueryString]:
        base = f"INSERT INTO {self.table._meta.tablename}"
        columns = ",".join([f'"{i._meta.name}"' for i in self.table._meta.columns])
        values = ",".join(["{}" for i in self.add_delegate._add])
        query = f"{base} ({columns}) VALUES {values} RETURNING id"
        return [
            QueryString(
                query,
                *[i.querystring for i in self.add_delegate._add],
                query_type="insert",
            )
        ]
