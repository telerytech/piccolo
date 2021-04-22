from __future__ import annotations

import copy
import decimal
import typing as t
import uuid
from datetime import date, datetime, time, timedelta

from piccolo.columns.base import Column, ForeignKeyMeta, OnDelete, OnUpdate
from piccolo.columns.defaults.date import DateArg, DateCustom, DateNow
from piccolo.columns.defaults.interval import IntervalArg, IntervalCustom
from piccolo.columns.defaults.time import TimeArg, TimeCustom, TimeNow
from piccolo.columns.defaults.timestamp import (TimestampArg, TimestampCustom,
                                                TimestampNow)
from piccolo.columns.defaults.timestamptz import (TimestamptzArg,
                                                  TimestamptzCustom,
                                                  TimestamptzNow)
from piccolo.columns.defaults.uuid import UUID4, UUIDArg
from piccolo.columns.operators.string import ConcatPostgres, ConcatSQLite
from piccolo.columns.reference import LazyTableReference
from piccolo.querystring import QueryString, Unquoted
from piccolo.utils.encoding import dump_json

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.columns.base import ColumnMeta
    from piccolo.table import Table


###############################################################################


class ConcatDelegate:
    """
    Used in update queries to concatenate two strings - for example:

    await Band.update({Band.name: Band.name + 'abc'}).run()
    """

    def get_querystring(
        self,
        column_name: str,
        value: t.Union[str, Varchar, Text],
        engine_type: str,
        reverse=False,
    ):
        Concat = ConcatPostgres if engine_type == "postgres" else ConcatSQLite

        if isinstance(value, (Varchar, Text)):
            column: Column = value
            if len(column._meta.call_chain) > 0:
                raise ValueError(
                    "Adding values across joins isn't currently supported."
                )
            other_column_name = column._meta.name
            if reverse:
                return QueryString(
                    Concat.template.format(
                        value_1=other_column_name, value_2=column_name
                    )
                )
            else:
                return QueryString(
                    Concat.template.format(
                        value_1=column_name, value_2=other_column_name
                    )
                )
        elif isinstance(value, str):
            if reverse:
                value_1 = QueryString("CAST({} AS text)", value)
                return QueryString(
                    Concat.template.format(value_1="{}", value_2=column_name),
                    value_1,
                )
            else:
                value_2 = QueryString("CAST({} AS text)", value)
                return QueryString(
                    Concat.template.format(value_1=column_name, value_2="{}"),
                    value_2,
                )
        else:
            raise ValueError(
                "Only str, Varchar columns, and Text columns can be added."
            )


class MathDelegate:
    """
    Used in update queries to perform math operations on columns, for example:

    await Band.update({Band.popularity: Band.popularity + 100}).run()
    """

    def get_querystring(
        self,
        column_name: str,
        operator: str,
        value: t.Union[int, float, Integer],
        reverse=False,
    ):
        if isinstance(value, Integer):
            column: Integer = value
            if len(column._meta.call_chain) > 0:
                raise ValueError(
                    "Adding values across joins isn't currently supported."
                )
            column_name = column._meta.name
            if reverse:
                return QueryString(f"{column_name} {operator} {column_name}")
            else:
                return QueryString(f"{column_name} {operator} {column_name}")
        elif isinstance(value, (int, float)):
            if reverse:
                return QueryString(f"{{}} {operator} {column_name}", value)
            else:
                return QueryString(f"{column_name} {operator} {{}}", value)
        else:
            raise ValueError(
                "Only integers, floats, and other Integer columns can be "
                "added."
            )


###############################################################################


class Varchar(Column):
    """
    Used for storing text when you want to enforce character length limits.
    Uses the ``str`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            name = Varchar(length=100)

        # Create
        >>> Band(name='Pythonistas').save().run_sync()

        # Query
        >>> Band.select(Band.name).run_sync()
        {'name': 'Pythonistas'}

    :param length:
        The maximum number of characters allowed.

    """

    value_type = str
    concat_delegate: ConcatDelegate = ConcatDelegate()

    def __init__(
        self,
        length: int = 255,
        default: t.Union[str, t.Callable[[], str], None] = "",
        **kwargs,
    ) -> None:
        self._validate_default(default, (str, None))

        self.length = length
        self.default = default
        kwargs.update({"length": length, "default": default})
        super().__init__(**kwargs)

    @property
    def column_type(self):
        if self.length:
            return f"VARCHAR({self.length})"
        else:
            return "VARCHAR"

    def __add__(self, value: t.Union[str, Varchar, Text]) -> QueryString:
        engine_type = self._meta.table._meta.db.engine_type
        return self.concat_delegate.get_querystring(
            column_name=self._meta.name, value=value, engine_type=engine_type,
        )

    def __radd__(self, value: t.Union[str, Varchar, Text]) -> QueryString:
        engine_type = self._meta.table._meta.db.engine_type
        return self.concat_delegate.get_querystring(
            column_name=self._meta.name,
            value=value,
            engine_type=engine_type,
            reverse=True,
        )


class Secret(Varchar):
    """
    The database treats it the same as a ``Varchar``, but Piccolo may treat it
    differently internally - for example, allowing a user to automatically
    omit any secret fields when doing a select query, to help prevent
    inadvertant leakage. A common use for a ``Secret`` field is a password.

    Uses the ``str`` type for values.

    **Example**

    .. code-block:: python

        class Door(Table):
            code = Secret(length=100)

        # Create
        >>> Door(code='123abc').save().run_sync()

        # Query
        >>> Door.select(Door.code).run_sync()
        {'code': '123abc'}

    """

    pass


class Text(Column):
    """
    Use when you want to store large strings, and don't want to limit the
    string size. Uses the ``str`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            name = Text()

        # Create
        >>> Band(name='Pythonistas').save().run_sync()

        # Query
        >>> Band.select(Band.name).run_sync()
        {'name': 'Pythonistas'}

    """

    value_type = str
    concat_delegate: ConcatDelegate = ConcatDelegate()

    def __init__(
        self, default: t.Union[str, None, t.Callable[[], str]] = "", **kwargs
    ) -> None:
        self._validate_default(default, (str, None))
        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)

    def __add__(self, value: t.Union[str, Varchar, Text]) -> QueryString:
        engine_type = self._meta.table._meta.db.engine_type
        return self.concat_delegate.get_querystring(
            column_name=self._meta.name, value=value, engine_type=engine_type
        )

    def __radd__(self, value: t.Union[str, Varchar, Text]) -> QueryString:
        engine_type = self._meta.table._meta.db.engine_type
        return self.concat_delegate.get_querystring(
            column_name=self._meta.name,
            value=value,
            engine_type=engine_type,
            reverse=True,
        )


class UUID(Column):
    """
    Used for storing UUIDs - in Postgres a UUID column type is used, and in
    SQLite it's just a Varchar. Uses the ``uuid.UUID`` type for values.

    **Example**

    .. code-block:: python

        import uuid

        class Band(Table):
            uuid = UUID()

        # Create
        >>> DiscountCode(code=uuid.uuid4()).save().run_sync()

        # Query
        >>> DiscountCode.select(DiscountCode.code).run_sync()
        {'code': UUID('09c4c17d-af68-4ce7-9955-73dcd892e462')}

    """

    value_type = uuid.UUID

    def __init__(self, default: UUIDArg = UUID4(), **kwargs) -> None:
        self._validate_default(default, UUIDArg.__args__)  # type: ignore

        if default == uuid.uuid4:
            default = UUID4()

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Integer(Column):
    """
    Used for storing whole numbers. Uses the ``int`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            popularity = Integer()

        # Create
        >>> Band(popularity=1000).save().run_sync()

        # Query
        >>> Band.select(Band.popularity).run_sync()
        {'popularity': 1000}

    """

    math_delegate = MathDelegate()

    def __init__(
        self, default: t.Union[int, t.Callable[[], int], None] = 0, **kwargs
    ) -> None:
        self._validate_default(default, (int, None))
        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)

    def __add__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name, operator="+", value=value
        )

    def __radd__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name,
            operator="+",
            value=value,
            reverse=True,
        )

    def __sub__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name, operator="-", value=value
        )

    def __rsub__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name,
            operator="-",
            value=value,
            reverse=True,
        )

    def __mul__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name, operator="*", value=value
        )

    def __rmul__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name,
            operator="*",
            value=value,
            reverse=True,
        )

    def __truediv__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name, operator="/", value=value
        )

    def __rtruediv__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name,
            operator="/",
            value=value,
            reverse=True,
        )

    def __floordiv__(self, value: t.Union[int, float, Integer]) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name, operator="/", value=value
        )

    def __rfloordiv__(
        self, value: t.Union[int, float, Integer]
    ) -> QueryString:
        return self.math_delegate.get_querystring(
            column_name=self._meta.name,
            operator="/",
            value=value,
            reverse=True,
        )


###############################################################################
# BigInt and SmallInt only exist on Postgres. SQLite treats them the same as
# Integer columns.


class BigInt(Integer):
    """
    In Postgres, this column supports large integers. In SQLite, it's an alias
    to an Integer column, which already supports large integers. Uses the
    ``int`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            value = BigInt()

        # Create
        >>> Band(popularity=1000000).save().run_sync()

        # Query
        >>> Band.select(Band.popularity).run_sync()
        {'popularity': 1000000}

    """

    @property
    def column_type(self):
        engine_type = self._meta.table._meta.db.engine_type
        if engine_type == "postgres":
            return "BIGINT"
        elif engine_type == "sqlite":
            return "INTEGER"
        raise Exception("Unrecognized engine type")


class SmallInt(Integer):
    """
    In Postgres, this column supports small integers. In SQLite, it's an alias
    to an Integer column. Uses the ``int`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            value = SmallInt()

        # Create
        >>> Band(popularity=1000).save().run_sync()

        # Query
        >>> Band.select(Band.popularity).run_sync()
        {'popularity': 1000}

    """

    @property
    def column_type(self):
        engine_type = self._meta.table._meta.db.engine_type
        if engine_type == "postgres":
            return "SMALLINT"
        elif engine_type == "sqlite":
            return "INTEGER"
        raise Exception("Unrecognized engine type")


###############################################################################


class Serial(Column):
    """
    An alias to an autoincremenring integer column in Postgres.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


DEFAULT = Unquoted("DEFAULT")
NULL = Unquoted("null")


class PrimaryKey(Column):
    @property
    def column_type(self):
        engine_type = self._meta.table._meta.db.engine_type
        if engine_type == "postgres":
            return "SERIAL"
        elif engine_type == "sqlite":
            return "INTEGER"
        raise Exception("Unrecognized engine type")

    def default(self):
        engine_type = self._meta.table._meta.db.engine_type
        if engine_type == "postgres":
            return DEFAULT
        elif engine_type == "sqlite":
            return NULL
        raise Exception("Unrecognized engine type")

    def __init__(self, **kwargs) -> None:
        # Set the index to False, as a database should automatically create
        # an index for a PrimaryKey column.
        kwargs.update({"primary": True, "key": True, "index": False})
        super().__init__(**kwargs)


###############################################################################


class Timestamp(Column):
    """
    Used for storing datetimes. Uses the ``datetime`` type for values.

    **Example**

    .. code-block:: python

        import datetime

        class Concert(Table):
            starts = Timestamp()

        # Create
        >>> Concert(
        >>>    starts=datetime.datetime(year=2050, month=1, day=1)
        >>> ).save().run_sync()

        # Query
        >>> Concert.select(Concert.starts).run_sync()
        {'starts': datetime.datetime(2050, 1, 1, 0, 0)}

    """

    value_type = datetime

    def __init__(
        self, default: TimestampArg = TimestampNow(), **kwargs
    ) -> None:
        self._validate_default(default, TimestampArg.__args__)  # type: ignore

        if isinstance(default, datetime):
            if default.tzinfo is not None:
                raise ValueError(
                    "Timestamp only stores timezone naive datetime objects - "
                    "use Timestamptz instead."
                )
            default = TimestampCustom.from_datetime(default)

        if default == datetime.now:
            default = TimestampNow()

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Timestamptz(Column):
    """
    Used for storing timezone aware datetimes. Uses the ``datetime`` type for
    values. The values are converted to UTC in the database, and are also
    returned as UTC.

    **Example**

    .. code-block:: python

        import datetime

        class Concert(Table):
            starts = Timestamptz()

        # Create
        >>> Concert(
        >>>    starts=datetime.datetime(
        >>>        year=2050, month=1, day=1, tzinfo=datetime.timezone.tz
        >>>    )
        >>> ).save().run_sync()

        # Query
        >>> Concert.select(Concert.starts).run_sync()
        {
            'starts': datetime.datetime(
                2050, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            )
        }

    """

    value_type = datetime

    def __init__(
        self, default: TimestamptzArg = TimestamptzNow(), **kwargs
    ) -> None:
        self._validate_default(
            default, TimestamptzArg.__args__  # type: ignore
        )

        if isinstance(default, datetime):
            default = TimestamptzCustom.from_datetime(default)

        if default == datetime.now:
            default = TimestamptzNow()

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Date(Column):
    """
    Used for storing dates. Uses the ``date`` type for values.

    **Example**

    .. code-block:: python

        import datetime

        class Concert(Table):
            starts = Date()

        # Create
        >>> Concert(
        >>>     starts=datetime.date(year=2020, month=1, day=1)
        >>> ).save().run_sync()

        # Query
        >>> Concert.select(Concert.starts).run_sync()
        {'starts': datetime.date(2020, 1, 1)}

    """

    value_type = date

    def __init__(self, default: DateArg = DateNow(), **kwargs) -> None:
        self._validate_default(default, DateArg.__args__)  # type: ignore

        if isinstance(default, date):
            default = DateCustom.from_date(default)

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Time(Column):
    """
    Used for storing times. Uses the ``time`` type for values.

    **Example**

    .. code-block:: python

        import datetime

        class Concert(Table):
            starts = Time()

        # Create
        >>> Concert(
        >>>    starts=datetime.time(hour=20, minute=0, second=0)
        >>> ).save().run_sync()

        # Query
        >>> Concert.select(Concert.starts).run_sync()
        {'starts': datetime.time(20, 0, 0)}

    """

    value_type = time

    def __init__(self, default: TimeArg = TimeNow(), **kwargs) -> None:
        self._validate_default(default, TimeArg.__args__)  # type: ignore

        if isinstance(default, time):
            default = TimeCustom.from_time(default)

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Interval(Column):  # lgtm [py/missing-equals]
    """
    Used for storing timedeltas. Uses the ``timedelta`` type for values.

    **Example**

    .. code-block:: python

        from datetime import timedelta

        class Concert(Table):
            duration = Interval()

        # Create
        >>> Concert(
        >>>    duration=timedelta(hours=2)
        >>> ).save().run_sync()

        # Query
        >>> Concert.select(Concert.duration).run_sync()
        {'duration': datetime.timedelta(seconds=7200)}

    """

    value_type = timedelta

    def __init__(
        self, default: IntervalArg = IntervalCustom(), **kwargs
    ) -> None:
        self._validate_default(default, IntervalArg.__args__)  # type: ignore

        if isinstance(default, timedelta):
            default = IntervalCustom.from_timedelta(default)

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)

    @property
    def column_type(self):
        engine_type = self._meta.table._meta.db.engine_type
        if engine_type == "postgres":
            return "INTERVAL"
        elif engine_type == "sqlite":
            # We can't use 'INTERVAL' because the type affinity in SQLite would
            # make it an integer - but we need a numeric field.
            # https://sqlite.org/datatype3.html#determination_of_column_affinity
            return "SECONDS"
        raise Exception("Unrecognized engine type")


###############################################################################


class Boolean(Column):
    """
    Used for storing True / False values. Uses the ``bool`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            has_drummer = Boolean()

        # Create
        >>> Band(has_drummer=True).save().run_sync()

        # Query
        >>> Band.select(Band.has_drummer).run_sync()
        {'has_drummer': True}

    """

    value_type = bool

    def __init__(
        self,
        default: t.Union[bool, t.Callable[[], bool], None] = False,
        **kwargs,
    ) -> None:
        self._validate_default(default, (bool, None))
        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


###############################################################################


class Numeric(Column):
    """
    Used for storing decimal numbers, when precision is important. An example
    use case is storing financial data. The value is returned as a ``Decimal``.

    **Example**

    .. code-block:: python

        from decimal import Decimal

        class Ticket(Table):
            price = Numeric(digits=(5,2))

        # Create
        >>> Ticket(price=Decimal('50.0')).save().run_sync()

        # Query
        >>> Ticket.select(Ticket.price).run_sync()
        {'price': Decimal('50.0')}

    :arg digits:
        When creating the column, you specify how many digits are allowed
        using a tuple. The first value is the `precision`, which is the
        total number of digits allowed. The second value is the `range`,
        which specifies how many of those digits are after the decimal
        point. For example, to store monetary values up to £999.99, the
        digits argument is `(5,2)`.

    """

    value_type = decimal.Decimal

    @property
    def column_type(self):
        if self.digits:
            return f"NUMERIC({self.precision}, {self.scale})"
        else:
            return "NUMERIC"

    @property
    def precision(self):
        """
        The total number of digits allowed.
        """
        return self.digits[0]

    @property
    def scale(self):
        """
        The number of digits after the decimal point.
        """
        return self.digits[1]

    def __init__(
        self,
        digits: t.Optional[t.Tuple[int, int]] = None,
        default: t.Union[
            decimal.Decimal, t.Callable[[], decimal.Decimal], None
        ] = decimal.Decimal(0.0),
        **kwargs,
    ) -> None:
        if isinstance(digits, tuple):
            if len(digits) != 2:
                raise ValueError(
                    "The `digits` argument should be a tuple of length 2, "
                    "with the first value being the precision, and the second "
                    "value being the scale."
                )
        else:
            if digits is not None:
                raise ValueError("The digits argument should be a tuple.")

        self._validate_default(default, (decimal.Decimal, None))

        self.default = default
        self.digits = digits
        kwargs.update({"default": default, "digits": digits})
        super().__init__(**kwargs)


class Decimal(Numeric):
    """
    An alias for Numeric.
    """

    pass


class Real(Column):
    """
    Can be used instead of ``Numeric`` for storing numbers, when precision
    isn't as important. The ``float`` type is used for values.

    **Example**

    .. code-block:: python

        class Concert(Table):
            rating = Real()

        # Create
        >>> Concert(rating=7.8).save().run_sync()

        # Query
        >>> Concert.select(Concert.rating).run_sync()
        {'rating': 7.8}

    """

    value_type = float

    def __init__(
        self,
        default: t.Union[float, t.Callable[[], float], None] = 0.0,
        **kwargs,
    ) -> None:
        self._validate_default(default, (float, None))
        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Float(Real):
    """
    An alias for Real.
    """

    pass


###############################################################################


class ForeignKey(Integer):
    """
    Used to reference another table. Uses the ``int`` type for values.

    **Example**

    .. code-block:: python

        class Band(Table):
            manager = ForeignKey(references=Manager)

        # Create
        >>> Band(manager=1).save().run_sync()

        # Query
        >>> Band.select(Band.manager).run_sync()
        {'manager': 1}

        # Query object
        >>> band = await Band.objects().first().run()
        >>> band.manager
        1

    **Joins**

    Can also use it to perform joins:

    .. code-block:: python

        >>> await Band.select(Band.name, Band.manager.name).first().run()
        {'name': 'Pythonistas', 'manager.name': 'Guido'}

    To get a referenced row as an object:

    .. code-block:: python

        manager = await Manager.objects().where(
            Manager.id == some_band.manager
        ).run()

    Or use either of the following, which are just a proxy to the above:

    .. code-block:: python

        manager = await band.get_related('manager').run()
        manager = await band.get_related(Band.manager).run()

    To change the manager:

    .. code-block:: python

        band.manager = some_manager_id
        await band.save().run()

    :param references:
        The ``Table`` being referenced.

        .. code-block:: python

            class Band(Table):
                manager = ForeignKey(references=Manager)

        A table can have a reference to itself, if you pass a ``references``
        argument of ``'self'``.

        .. code-block:: python

            class Musician(Table):
                name = Varchar(length=100)
                instructor = ForeignKey(references='self')

        In certain situations, you may be unable to reference a ``Table`` class
        if it causes a circular dependency. Try and avoid these by refactoring
        your code. If unavoidable, you can specify a lazy reference. If the
        ``Table`` is defined in the same file:

        .. code-block:: python

            class Band(Table):
                manager = ForeignKey(references='Manager')

        If the ``Table`` is defined in a Piccolo app:

        .. code-block:: python

            from piccolo.columns.reference import LazyTableReference

            class Band(Table):
                manager = ForeignKey(
                    references=LazyTableReference(
                       table_class_name="Manager", app_name="my_app",
                    )
                )

        If you aren't using Piccolo apps, you can specify a ``Table`` in any
        Python module:

        .. code-block:: python

            from piccolo.columns.reference import LazyTableReference

            class Band(Table):
                manager = ForeignKey(
                    references=LazyTableReference(
                       table_class_name="Manager",
                       module_path="some_module.tables",
                    )
                    # Alternatively, Piccolo will interpret this string as
                    # the same as above:
                    # references="some_module.tables.Manager"
                )

    :param on_delete:
        Determines what the database should do when a row is deleted with
        foreign keys referencing it. If set to ``OnDelete.cascade``, any rows
        referencing the deleted row are also deleted.

        Options:

            * ``OnDelete.cascade`` (default)
            * ``OnDelete.restrict``
            * ``OnDelete.no_action``
            * ``OnDelete.set_null``
            * ``OnDelete.set_default``

        To learn more about the different options, see the `Postgres docs <https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK>`_.

        .. code-block:: python

            from piccolo.columns import OnDelete

            class Band(Table):
                name = ForeignKey(
                    references=Manager,
                    on_delete=OnDelete.cascade
                )

    :param on_update:
        Determines what the database should do when a row has it's primary key
        updated. If set to ``OnDelete.cascade``, any rows referencing the
        updated row will have their references updated to point to the new
        primary key.

        Options:

            * ``OnUpdate.cascade`` (default)
            * ``OnUpdate.restrict``
            * ``OnUpdate.no_action``
            * ``OnUpdate.set_null``
            * ``OnUpdate.set_default``

        To learn more about the different options, see the `Postgres docs <https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK>`_.

        .. code-block:: python

            from piccolo.columns import OnDelete

            class Band(Table):
                name = ForeignKey(
                    references=Manager,
                    on_update=OnUpdate.cascade
                )

    """  # noqa: E501

    column_type = "INTEGER"

    def __init__(
        self,
        references: t.Union[t.Type[Table], LazyTableReference, str],
        default: t.Union[int, None] = None,
        null: bool = True,
        on_delete: OnDelete = OnDelete.cascade,
        on_update: OnUpdate = OnUpdate.cascade,
        **kwargs,
    ) -> None:
        self._validate_default(default, (int, None))

        kwargs.update(
            {
                "references": references,
                "on_delete": on_delete,
                "on_update": on_update,
            }
        )
        super().__init__(default=default, null=null, **kwargs)

        # This is here just for type inference - the actual value is set by
        # the Table metaclass. We can't set the actual value here, as
        # only the metaclass has access to the table.
        from piccolo.table import Table

        self._foreign_key_meta = ForeignKeyMeta(
            Table, OnDelete.cascade, OnUpdate.cascade
        )

    def copy(self) -> ForeignKey:
        column: ForeignKey = copy.copy(self)
        column._meta = self._meta.copy()
        column._foreign_key_meta = self._foreign_key_meta.copy()
        return column

    def set_proxy_columns(self):
        """
        In order to allow a fluent interface, where tables can be traversed
        using ForeignKeys (e.g. ``Band.manager.name``), we add attributes to
        the ``ForeignKey`` column for each column in the table being pointed
        to.
        """
        _foreign_key_meta = object.__getattribute__(self, "_foreign_key_meta")
        for column in _foreign_key_meta.resolved_references._meta.columns:
            _column: Column = column.copy()
            setattr(self, _column._meta.name, _column)
            _foreign_key_meta.proxy_columns.append(_column)

    def __getattribute__(self, name: str):
        """
        Returns attributes unmodified unless they're Column instances, in which
        case a copy is returned with an updated call_chain (which records the
        joins required).
        """
        # If the ForeignKey is using a lazy reference, we need to set the
        # attributes here. Attributes starting with a double underscore are
        # unlikely to be column names.
        if not name.startswith("__"):
            try:
                _foreign_key_meta = object.__getattribute__(
                    self, "_foreign_key_meta"
                )
            except AttributeError:
                pass
            else:
                if _foreign_key_meta.proxy_columns == [] and isinstance(
                    _foreign_key_meta.references, LazyTableReference
                ):
                    object.__getattribute__(self, "set_proxy_columns")()

        try:
            value = object.__getattribute__(self, name)
        except AttributeError:
            raise AttributeError

        foreignkey_class: t.Type[ForeignKey] = object.__getattribute__(
            self, "__class__"
        )

        if isinstance(value, foreignkey_class):  # i.e. a ForeignKey
            new_column = value.copy()
            new_column._meta.call_chain.append(self)

            # We have to set limits to the call chain because Table 1 can
            # reference Table 2, which references Table 1, creating an endless
            # loop. For now an arbitrary limit is set of 10 levels deep.
            # When querying a call chain more than 10 levels deep, an error
            # will be raised. Often there are more effective ways of
            # structuring a query than joining so many tables anyway.
            if len(new_column._meta.call_chain) >= 10:
                raise Exception("Call chain too long!")

            foreign_key_meta: ForeignKeyMeta = object.__getattribute__(
                self, "_foreign_key_meta"
            )

            for proxy_column in foreign_key_meta.proxy_columns:
                try:
                    delattr(new_column, proxy_column._meta.name)
                except Exception:
                    pass

            for (
                column
            ) in value._foreign_key_meta.resolved_references._meta.columns:
                _column: Column = column.copy()
                _column._meta.call_chain = [
                    i for i in new_column._meta.call_chain
                ]
                _column._meta.call_chain.append(new_column)
                if _column._meta.name == "id":
                    continue
                setattr(new_column, _column._meta.name, _column)
                foreign_key_meta.proxy_columns.append(_column)

            return new_column
        elif issubclass(type(value), Column):
            new_column = value.copy()

            column_meta: ColumnMeta = object.__getattribute__(self, "_meta")

            new_column._meta.call_chain = column_meta.call_chain.copy()
            new_column._meta.call_chain.append(self)
            return new_column
        else:
            return value


###############################################################################


class JSON(Column):  # lgtm[py/missing-equals]
    """
    Used for storing JSON strings. The data is stored as text. This can be
    preferable to JSONB if you just want to store and retrieve JSON without
    querying it directly. It works with SQLite and Postgres.

    :param default:
        Either a JSON string can be provided, or a Python ``dict`` or ``list``
        which is then converted to a JSON string.

    """

    value_type = str

    def __init__(
        self,
        default: t.Union[
            str,
            t.List,
            t.Dict,
            t.Callable[[], t.Union[str, t.List, t.Dict]],
            None,
        ] = "{}",
        **kwargs,
    ) -> None:
        self._validate_default(default, (str, list, dict, None))

        if isinstance(default, (list, dict)):
            default = dump_json(default)

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)

        self.json_operator: t.Optional[str] = None


class JSONB(JSON):
    """
    Used for storing JSON strings - Postgres only. The data is stored in a
    binary format, and can be queried. Insertion can be slower (as it needs to
    be converted to the binary format). The benefits of JSONB generally
    outweigh the downsides.

    :param default:
        Either a JSON string can be provided, or a Python ``dict`` or ``list``
        which is then converted to a JSON string.

    """

    def arrow(self, key: str) -> JSONB:
        """
        Allows part of the JSON structure to be returned - for example,
        for {"a": 1}, and a key value of "a", then 1 will be returned.
        """
        self.json_operator = f"-> '{key}'"
        return self

    def get_select_string(self, engine_type: str, just_alias=False) -> str:
        select_string = self._meta.get_full_name(just_alias=just_alias)
        if self.json_operator is None:
            return select_string
        else:
            if self.alias is None:
                return f"{select_string} {self.json_operator}"
            else:
                return f"{select_string} {self.json_operator} AS {self.alias}"


###############################################################################


class Bytea(Column):
    """
    Used for storing bytes.

    **Example**

    .. code-block:: python

        class Token(Table):
            token = Bytea(default=b'token123')

        # Create
        >>> Token(token=b'my-token').save().run_sync()

        # Query
        >>> Token.select(Token.token).run_sync()
        {'token': b'my-token'}

    """

    value_type = bytes

    @property
    def column_type(self):
        engine_type = self._meta.table._meta.db.engine_type
        if engine_type == "postgres":
            return "BYTEA"
        elif engine_type == "sqlite":
            return "BLOB"
        raise Exception("Unrecognized engine type")

    def __init__(
        self,
        default: t.Union[
            bytes,
            bytearray,
            t.Callable[[], bytes],
            t.Callable[[], bytearray],
            None,
        ] = b"",
        **kwargs,
    ) -> None:
        self._validate_default(default, (bytes, bytearray, None))

        if isinstance(default, bytearray):
            default = bytes(default)

        self.default = default
        kwargs.update({"default": default})
        super().__init__(**kwargs)


class Blob(Bytea):
    """
    An alias for Bytea.
    """

    pass
