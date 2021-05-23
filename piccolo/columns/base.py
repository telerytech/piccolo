from __future__ import annotations
from abc import ABCMeta, abstractmethod
import copy
from dataclasses import dataclass, field
import datetime
import decimal
from enum import Enum
import inspect
import typing as t

from piccolo.columns.operators.comparison import (
    ComparisonOperator,
    Equal,
    GreaterEqualThan,
    GreaterThan,
    ILike,
    In,
    IsNotNull,
    IsNull,
    LessEqualThan,
    LessThan,
    Like,
    NotEqual,
    NotIn,
    NotLike,
)
from piccolo.columns.combination import Where
from piccolo.columns.defaults.base import Default
from piccolo.columns.reference import LazyTableReference
from piccolo.columns.indexes import IndexMethod
from piccolo.querystring import QueryString
from piccolo.utils.warnings import colored_warning

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.columns.column_types import ForeignKey
    from piccolo.table import Table


class OnDelete(str, Enum):
    cascade = "CASCADE"
    restrict = "RESTRICT"
    no_action = "NO ACTION"
    set_null = "SET NULL"
    set_default = "SET DEFAULT"

    def __str__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def __repr__(self):
        return self.__str__()


class OnUpdate(str, Enum):
    cascade = "CASCADE"
    restrict = "RESTRICT"
    no_action = "NO ACTION"
    set_null = "SET NULL"
    set_default = "SET DEFAULT"

    def __str__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def __repr__(self):
        return self.__str__()


@dataclass
class ForeignKeyMeta:
    references: t.Union[t.Type[Table], LazyTableReference]
    on_delete: OnDelete
    on_update: OnUpdate
    proxy_columns: t.List[Column] = field(default_factory=list)

    @property
    def resolved_references(self) -> t.Type[Table]:
        """
        Evaluates the ``references`` attribute if it's a LazyTableReference,
        raising a ``ValueError`` if it fails, otherwise returns a ``Table``
        subclass.
        """
        from piccolo.table import Table

        if isinstance(self.references, LazyTableReference):
            return self.references.resolve()
        elif inspect.isclass(self.references) and issubclass(
            self.references, Table
        ):
            return self.references
        else:
            raise ValueError(
                "The references attribute is neither a Table sublclass or a "
                "LazyTableReference instance."
            )

    def copy(self) -> ForeignKeyMeta:
        kwargs = self.__dict__.copy()
        kwargs.update(proxy_columns=self.proxy_columns.copy())
        return self.__class__(**kwargs)

    def __copy__(self) -> ForeignKeyMeta:
        return self.copy()

    def __deepcopy__(self, memo) -> ForeignKeyMeta:
        """
        We override deepcopy, as it's too slow if it has to recreate
        everything.
        """
        return self.copy()


@dataclass
class ColumnMeta:
    """
    We store as many attributes in ColumnMeta as possible, to help avoid name
    clashes with user defined attributes.
    """

    # General attributes:
    null: bool = False
    primary: bool = False
    key: bool = False
    unique: bool = False
    index: bool = False
    index_method: IndexMethod = IndexMethod.btree
    required: bool = False
    help_text: t.Optional[str] = None
    choices: t.Optional[Enum] = None

    # Used for representing the table in migrations and the playground.
    params: t.Dict[str, t.Any] = field(default_factory=dict)

    # Set by the Table Metaclass:
    _name: t.Optional[str] = None
    _table: t.Optional[t.Type[Table]] = None

    # Used by Foreign Keys:
    call_chain: t.List["ForeignKey"] = field(default_factory=lambda: [])
    table_alias: t.Optional[str] = None

    @property
    def name(self) -> str:
        if not self._name:
            raise ValueError(
                "`_name` isn't defined - the Table Metaclass should set it."
            )
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def table(self) -> t.Type[Table]:
        if not self._table:
            raise ValueError(
                "`_table` isn't defined - the Table Metaclass should set it."
            )
        return self._table

    @property
    def engine_type(self) -> str:
        engine = self.table._meta.db
        if engine:
            return engine.engine_type
        else:
            raise ValueError("The table has no engine defined.")

    @property
    def get_choices(self) -> Optional(list):
        """
        Returns choices as a list of choice tuples (choice name, value. Custom fields should add type checking to keys as well
        """
        if isinstance(self.choices, t.Enum):
            return [(choice.name.replace("_", " ").title(), choice.value) for choice in self.choices]
        elif isinstance(self.choices, tuple):
            return list(self.choices) # Guarantee a list
        elif isinstance(self.choices, list):
            return self.choices
        else:
            return None

    def get_full_name(self, just_alias=False) -> str:
        """
        Returns the full column name, taking into account joins.
        """
        column_name = self.name

        if not self.call_chain:
            return f"{self.table._meta.tablename}.{column_name}"

        column_name = (
            "$".join([i._meta.name for i in self.call_chain])
            + f"${column_name}"
        )
        alias = f"{self.call_chain[-1]._meta.table_alias}.{self.name}"
        if just_alias:
            return alias
        else:
            return f'{alias} AS "{column_name}"'

    def copy(self) -> ColumnMeta:
        kwargs = self.__dict__.copy()
        kwargs.update(
            params=self.params.copy(), call_chain=self.call_chain.copy(),
        )
        return self.__class__(**kwargs)

    def __copy__(self) -> ColumnMeta:
        return self.copy()

    def __deepcopy__(self, memo) -> ColumnMeta:
        """
        We override deepcopy, as it's too slow if it has to recreate
        everything.
        """
        return self.copy()


class Selectable(metaclass=ABCMeta):
    @abstractmethod
    def get_select_string(self, engine_type: str, just_alias=False) -> str:
        """
        In a query, what to output after the select statement - could be a
        column name, a sub query, a function etc. For a column it will be the
        column name.
        """
        pass


class Column(Selectable):
    """
    All other columns inherit from ``Column``. Don't use it directly.

    The following arguments apply to all column types:

    :param null:
        Whether the column is nullable.

    :param primary:
        If set, the column is used as a primary key.

    :param key:
        If set, the column is treated as a key.

    :param default:
        The column value to use if not specified by the user.

    :param unique:
        If set, a unique contraint will be added to the column.

    :param index:
        Whether an index is created for the column, which can improve
        the speed of selects, but can slow down inserts.

    :param index_method:
        If index is set to True, this specifies what type of index is created.

    :param required:
        This isn't used by the database - it's to indicate to other tools that
        the user must provide this value. Example uses are in serialisers for
        API endpoints, and form fields.

    :param help_text:
        This provides some context about what the column is being used for. For
        example, for a `Decimal` column called `value`, it could say
        'The units are millions of dollars'. The database doesn't use this
        value, but tools such as Piccolo Admin use it to show a tooltip in the
        GUI.

    """

    value_type: t.Type = int

    def __init__(
        self,
        null: bool = False,
        primary: bool = False,
        key: bool = False,
        unique: bool = False,
        index: bool = False,
        index_method: IndexMethod = IndexMethod.btree,
        required: bool = False,
        help_text: t.Optional[str] = None,
        **kwargs,
    ) -> None:
        # Used for migrations.
        # We deliberately omit 'required', and 'help_text' as they don't effect
        # the actual schema.
        kwargs.update(
            {
                "null": null,
                "primary": primary,
                "key": key,
                "unique": unique,
                "index": index,
                "index_method": index_method,
            }
        )

        if kwargs.get("default", ...) is None and not null:
            raise ValueError(
                "A default value of None isn't allowed if the column is "
                "not nullable."
            )

        self._meta = ColumnMeta(
            null=null,
            primary=primary,
            key=key,
            unique=unique,
            index=index,
            index_method=index_method,
            params=kwargs,
            required=required,
            help_text=help_text,
        )

        self.alias: t.Optional[str] = None

    def _validate_default(
        self,
        default: t.Any,
        allowed_types: t.Iterable[t.Union[None, t.Type[t.Any]]],
    ) -> bool:
        """
        Make sure that the default value is of the allowed types.
        """
        if getattr(self, "_validated", None):
            # If it has previously been validated by a subclass, don't
            # validate again.
            return True
        elif (
            default is None
            and None in allowed_types
            or type(default) in allowed_types
        ):
            self._validated = True
            return True
        elif callable(default):
            self._validated = True
            return True
        else:
            raise ValueError(
                f"The default {default} isn't one of the permitted types - "
                f"{allowed_types}"
            )

    def is_in(self, values: t.List[t.Any]) -> Where:
        if len(values) == 0:
            raise ValueError(
                "The `values` list argument must contain at least one value."
            )
        return Where(column=self, values=values, operator=In)

    def not_in(self, values: t.List[t.Any]) -> Where:
        if len(values) == 0:
            raise ValueError(
                "The `values` list argument must contain at least one value."
            )
        return Where(column=self, values=values, operator=NotIn)

    def like(self, value: str) -> Where:
        if "%" not in value:
            raise ValueError("% is required for like operators")
        return Where(column=self, value=value, operator=Like)

    def ilike(self, value: str) -> Where:
        if "%" not in value:
            raise ValueError("% is required for ilike operators")
        if self._meta.engine_type == "postgres":
            operator: t.Type[ComparisonOperator] = ILike
        else:
            colored_warning(
                "SQLite doesn't support ILIKE currently, falling back to LIKE."
            )
            operator = Like
        return Where(column=self, value=value, operator=operator)

    def not_like(self, value: str) -> Where:
        if "%" not in value:
            raise ValueError("% is required for like operators")
        return Where(column=self, value=value, operator=NotLike)

    def __lt__(self, value) -> Where:
        return Where(column=self, value=value, operator=LessThan)

    def __le__(self, value) -> Where:
        return Where(column=self, value=value, operator=LessEqualThan)

    def __gt__(self, value) -> Where:
        return Where(column=self, value=value, operator=GreaterThan)

    def __ge__(self, value) -> Where:
        return Where(column=self, value=value, operator=GreaterEqualThan)

    def __eq__(self, value) -> Where:  # type: ignore
        if value is None:
            return Where(column=self, operator=IsNull)
        else:
            return Where(column=self, value=value, operator=Equal)

    def __ne__(self, value) -> Where:  # type: ignore
        if value is None:
            return Where(column=self, operator=IsNotNull)
        else:
            return Where(column=self, value=value, operator=NotEqual)

    def __hash__(self):
        return hash(self._meta.name)

    def is_null(self) -> Where:
        """
        Can be used instead of `MyTable.column != None`, because some linters
        don't like a comparison to None.
        """
        return Where(column=self, operator=IsNull)

    def is_not_null(self) -> Where:
        """
        Can be used instead of `MyTable.column == None`, because some linters
        don't like a comparison to None.
        """
        return Where(column=self, operator=IsNotNull)

    def as_alias(self, name: str) -> Column:
        """
        Allows column names to be changed in the result of a select.

        For example:

        >>> await Band.select(Band.name.as_alias('title')).run()
        {'title': 'Pythonistas'}

        """
        column = copy.deepcopy(self)
        column.alias = name
        return column

    def get_default_value(self) -> t.Any:
        """
        If the column has a default attribute, return it. If it's callable,
        return the response instead.
        """
        default = getattr(self, "default", ...)
        if default is not ...:
            default = default.value if isinstance(default, Enum) else default
            is_callable = hasattr(default, "__call__")
            value = default() if is_callable else default
            return value
        return None

    def get_select_string(self, engine_type: str, just_alias=False) -> str:
        """
        How to refer to this column in a SQL query.
        """
        if self.alias is None:
            return self._meta.get_full_name(just_alias=just_alias)
        else:
            original_name = self._meta.get_full_name(just_alias=True)
            return f"{original_name} AS {self.alias}"

    def get_where_string(self, engine_type: str) -> str:
        return self.get_select_string(engine_type=engine_type, just_alias=True)

    def get_sql_value(self, value: t.Any) -> t.Any:
        """
        When using DDL statements, we can't parameterise the values. An example
        is when setting the default for a column. So we have to convert from
        the Python type to a string representation which we can include in our
        DDL statements.

        :param value:
            The Python value to convert to a string usable in a DDL statement
            e.g. 1.
        :returns:
            The string usable in the DDL statement e.g. '1'.

        """
        if isinstance(value, Default):
            output = getattr(value, self._meta.engine_type)
        elif value is None:
            output = "null"
        elif isinstance(value, (float, decimal.Decimal)):
            output = str(value)
        elif isinstance(value, str):
            output = f"'{value}'"
        elif isinstance(value, bool):
            output = str(value).lower()
        elif isinstance(value, datetime.datetime):
            output = f"'{value.isoformat().replace('T', '')}'"
        elif isinstance(value, bytes):
            output = f"'{value.hex()}'"
        elif isinstance(value, list):
            # Convert to the array syntax.
            output = (
                "'{" + ", ".join([self.get_sql_value(i) for i in value]) + "}'"
            )
        else:
            output = value

        return output

    @property
    def column_type(self):
        return self.__class__.__name__.upper()

    @property
    def querystring(self) -> QueryString:
        """
        Used when creating tables.
        """
        query = f'"{self._meta.name}" {self.column_type}'
        if self._meta.primary:
            query += " PRIMARY"
        if self._meta.key:
            query += " KEY"
        if self._meta.unique:
            query += " UNIQUE"
        if not self._meta.null:
            query += " NOT NULL"

        foreign_key_meta: t.Optional[ForeignKeyMeta] = getattr(
            self, "_foreign_key_meta", None
        )
        if foreign_key_meta:
            tablename = foreign_key_meta.resolved_references._meta.tablename
            on_delete = foreign_key_meta.on_delete.value
            on_update = foreign_key_meta.on_update.value
            query += (
                f" REFERENCES {tablename} (id)"
                f" ON DELETE {on_delete}"
                f" ON UPDATE {on_update}"
            )

        if not self._meta.primary:
            default = self.get_default_value()
            sql_value = self.get_sql_value(value=default)
            # Escape the value if it contains a pair of curly braces, otherwise
            # an empty value will appear in the compiled querystring.
            sql_value = (
                sql_value.replace("{}", "{{}}")
                if isinstance(sql_value, str)
                else sql_value
            )
            query += f" DEFAULT {sql_value}"

        return QueryString(query)

    def copy(self) -> Column:
        column: Column = copy.copy(self)
        column._meta = self._meta.copy()
        return column

    def __deepcopy__(self, memo) -> Column:
        """
        We override deepcopy, as it's too slow if it has to recreate
        everything.
        """
        return self.copy()

    def __str__(self):
        return self.querystring.__str__()

    def __repr__(self):
        try:
            table = self._meta.table
        except ValueError:
            table_class_name = "Unknown"
        else:
            table_class_name = table.__name__
        return (
            f"{table_class_name}.{self._meta.name} - "
            f"{self.__class__.__name__}"
        )
