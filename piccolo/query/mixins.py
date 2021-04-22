from __future__ import annotations

import typing as t
from dataclasses import dataclass, field

from piccolo.columns import And, Column, Or, Secret, Where
from piccolo.custom_types import Combinable
from piccolo.querystring import QueryString

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.columns.base import Selectable
    from piccolo.table import Table  # noqa


@dataclass
class Limit:
    __slots__ = ("number",)

    number: int

    def __post_init__(self):
        if type(self.number) != int:
            raise TypeError("Limit must be an integer")

    @property
    def querystring(self) -> QueryString:
        return QueryString(f" LIMIT {self.number}")

    def __str__(self) -> str:
        return self.querystring.__str__()


@dataclass
class Offset:
    __slots__ = ("number",)

    number: int

    def __post_init__(self):
        if type(self.number) != int:
            raise TypeError("Limit must be an integer")

    @property
    def querystring(self) -> QueryString:
        return QueryString(f" OFFSET {self.number}")

    def __str__(self) -> str:
        return self.querystring.__str__()


@dataclass
class OrderBy:
    __slots__ = ("columns", "ascending")

    columns: t.Sequence[Column]
    ascending: bool

    @property
    def querystring(self) -> QueryString:
        order = "ASC" if self.ascending else "DESC"
        columns_names = ", ".join(
            [i._meta.get_full_name(just_alias=True) for i in self.columns]
        )
        return QueryString(f" ORDER BY {columns_names} {order}")

    def __str__(self):
        return self.querystring.__str__()


@dataclass
class Output:

    as_json: bool = False
    as_list: bool = False
    as_objects: bool = False


@dataclass
class WhereDelegate:

    _where: t.Optional[Combinable] = None
    _where_columns: t.List[Column] = field(default_factory=list)

    def get_where_columns(self):
        """
        Retrieves all columns used in the where clause - in case joins are
        needed.
        """
        self._where_columns = []
        self._extract_columns(self._where)
        return self._where_columns

    def _extract_columns(self, combinable: Combinable):
        if isinstance(combinable, Where):
            self._where_columns.append(combinable.column)
        elif isinstance(combinable, And) or isinstance(combinable, Or):
            self._extract_columns(combinable.first)
            self._extract_columns(combinable.second)

    def where(self, where: Combinable):
        if self._where:
            self._where = And(self._where, where)
        else:
            self._where = where


@dataclass
class OrderByDelegate:

    _order_by: t.Optional[OrderBy] = None

    def get_order_by_columns(self) -> t.List[Column]:
        return list(self._order_by.columns) if self._order_by else []

    def order_by(self, *columns: Column, ascending=True):
        self._order_by = OrderBy(columns, ascending)


@dataclass
class LimitDelegate:

    _limit: t.Optional[Limit] = None
    _first = False

    def limit(self, number: int):
        self._limit = Limit(number)

    def first(self):
        self.limit(1)
        self._first = True


@dataclass
class DistinctDelegate:

    _distinct: bool = False

    def distinct(self):
        self._distinct = True


@dataclass
class CountDelegate:

    _count: bool = False

    def count(self):
        self._count = True


@dataclass
class AddDelegate:

    _add: t.List[Table] = field(default_factory=list)

    def add(self, *instances: Table, table_class: t.Type[Table]):
        for instance in instances:
            if not isinstance(instance, table_class):
                raise TypeError("Incompatible type added.")
        self._add += instances


@dataclass
class OutputDelegate:
    """
    Example usage:

    .output(as_list=True)
    .output(as_json=True)
    .output(as_json=True, as_list=True)
    """

    _output: Output = field(default_factory=Output)

    def output(
        self,
        as_list: t.Optional[bool] = None,
        as_json: t.Optional[bool] = None,
    ):
        """
        :param as_list:
            If each row only returns a single value, compile all of the results
            into a single list.
        :param as_json:
            The results are serialised into JSON. It's equivalent to running
            `json.dumps` on the result.
        """
        if as_list is not None:
            self._output.as_list = bool(as_list)

        if type(as_json) is bool:
            self._output.as_json = bool(as_json)


@dataclass
class ColumnsDelegate:
    """
    Example usage:

    .columns(MyTable.column_a, MyTable.column_b)
    """

    selected_columns: t.Sequence[Selectable] = field(default_factory=list)

    def columns(self, *columns: Selectable):
        combined = list(self.selected_columns) + list(columns)
        self.selected_columns = combined

    def remove_secret_columns(self):
        self.selected_columns = [
            i for i in self.selected_columns if not isinstance(i, Secret)
        ]


@dataclass
class ValuesDelegate:
    """
    Used to specify new column values - primarily used in update queries.

    Example usage:

    .values({MyTable.column_a: 1})
    """

    _values: t.Dict[Column, t.Any] = field(default_factory=dict)

    def values(self, values: t.Dict[Column, t.Any]):
        self._values.update(values)


@dataclass
class OffsetDelegate:
    """
    Used to offset the results - for example, to return row 100 and onward.

    Typically used in conjunction with order_by and limit.

    Example usage:

    .offset(100)
    """

    _offset: t.Optional[Offset] = None

    def offset(self, number: int = 0):
        self._offset = Offset(number)


@dataclass
class GroupBy:
    __slots__ = ("columns",)

    columns: t.Sequence[Column]

    @property
    def querystring(self) -> QueryString:
        columns_names = ", ".join(
            [i._meta.get_full_name(just_alias=True) for i in self.columns]
        )
        return QueryString(f" GROUP BY {columns_names}")

    def __str__(self):
        return self.querystring.__str__()


@dataclass
class GroupByDelegate:
    """
    Used to group results - needed when doing aggregation.

    .group_by(Band.name)
    """

    _group_by: t.Optional[GroupBy] = None

    def group_by(self, *columns: Column):
        self._group_by = GroupBy(columns=columns)
