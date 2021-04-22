from __future__ import annotations

import typing as t

from piccolo.columns.operators.comparison import ComparisonOperator
from piccolo.custom_types import Combinable, Iterable
from piccolo.querystring import QueryString

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.columns.base import Column  # noqa


class CombinableMixin(object):
    def __and__(self, value: Combinable) -> "And":
        return And(self, value)  # type: ignore

    def __or__(self, value: Combinable) -> "Or":
        return Or(self, value)  # type: ignore


class Combination(CombinableMixin):

    __slots__ = ("first", "second")

    operator = ""

    def __init__(self, first: Combinable, second: Combinable) -> None:
        self.first = first
        self.second = second

    @property
    def querystring(self) -> QueryString:
        return QueryString(
            "({} " + self.operator + " {})",
            self.first.querystring,
            self.second.querystring,
        )

    def __str__(self):
        self.querystring.__str__()


class And(Combination):
    operator = "AND"


class Or(Combination):
    operator = "OR"


class Undefined:
    pass


UNDEFINED = Undefined()


class WhereRaw(CombinableMixin):
    def __init__(self, sql: str, *args: t.Any) -> None:
        """
        Execute raw SQL queries in your where clause. Use with caution!

        await Band.where(
            WhereRaw("name = 'Pythonistas'")
        )

        Or passing in parameters:

        await Band.where(
            WhereRaw("name = {}", 'Pythonistas')
        )
        """
        self.querystring = QueryString(sql, *args)

    def __str__(self):
        return self.querystring.__str__()


class Where(CombinableMixin):

    __slots__ = ("column", "value", "values", "operator")

    def __init__(
        self,
        column: Column,
        value: t.Any = UNDEFINED,
        values: t.Union[Iterable, Undefined] = UNDEFINED,
        operator: t.Type[ComparisonOperator] = ComparisonOperator,
    ) -> None:
        """
        We use the UNDEFINED value to show the value was deliberately
        omitted, vs None, which is a valid value for a where clause.
        """
        self.column = column
        self.value = value
        self.values = values
        self.operator = operator

    @property
    def values_querystring(self) -> QueryString:
        if isinstance(self.values, Undefined):
            raise ValueError("values is undefined")

        template = ", ".join(["{}" for i in self.values])
        return QueryString(template, *self.values)

    @property
    def querystring(self) -> QueryString:
        args: t.List[t.Any] = []
        if self.value != UNDEFINED:
            args.append(self.value)
        if self.values != UNDEFINED:
            args.append(self.values_querystring)

        template = self.operator.template.format(
            name=self.column.get_where_string(
                engine_type=self.column._meta.engine_type
            ),
            value="{}",
            values="{}",
        )

        return QueryString(template, *args)

    def __str__(self):
        return self.querystring.__str__()
