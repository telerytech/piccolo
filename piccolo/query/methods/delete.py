from __future__ import annotations

import typing as t

from piccolo.custom_types import Combinable
from piccolo.query.base import Query
from piccolo.query.mixins import WhereDelegate
from piccolo.querystring import QueryString

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.table import Table


class DeletionError(Exception):
    pass


class Delete(Query):

    __slots__ = ("force", "where_delegate")

    def __init__(self, table: t.Type[Table], force: bool = False):
        super().__init__(table)
        self.force = force
        self.where_delegate = WhereDelegate()

    def where(self, where: Combinable) -> Delete:
        self.where_delegate.where(where)
        return self

    def _validate(self):
        """
        Don't let a deletion happen unless it has a where clause, or is
        explicitly forced.
        """
        if (not self.where_delegate._where) and (not self.force):
            classname = self.table.__name__
            raise DeletionError(
                "Do you really want to delete all the data from "
                f"{classname}? If so, use {classname}.delete(force=True)."
            )

    async def run_pre_functions(self):
        for function in self.table._meta.pre_delete:
            function()

    async def run_post_functions(self):
        for function in self.table._meta.post_delete:
            function()

    def run_pre_functions_sync(self):
        for function in self.table._meta.pre_delete:
            function()

    def run_post_functions_sync(self):
        for function in self.table._meta.post_delete:
            function()

    @property
    def querystrings(self) -> t.Sequence[QueryString]:
        query = f"DELETE FROM {self.table._meta.tablename}"
        if self.where_delegate._where:
            query += " WHERE {}"
            return [QueryString(query, self.where_delegate._where.querystring)]
        else:
            return [QueryString(query)]
