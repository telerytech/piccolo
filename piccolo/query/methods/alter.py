from __future__ import annotations

import itertools
import typing as t
from dataclasses import dataclass

from piccolo.columns.base import Column, OnDelete, OnUpdate
from piccolo.columns.column_types import ForeignKey, Numeric, Varchar
from piccolo.query.base import Query
from piccolo.querystring import QueryString
from piccolo.utils.warnings import Level, colored_warning

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.table import Table


@dataclass
class AlterStatement:
    __slots__ = tuple()  # type: ignore

    def querystring(self) -> QueryString:
        raise NotImplementedError()

    def __str__(self) -> str:
        return self.querystring.__str__()


@dataclass
class RenameTable(AlterStatement):
    __slots__ = ("new_name",)

    new_name: str

    @property
    def querystring(self) -> QueryString:
        return QueryString(f"RENAME TO {self.new_name}")


@dataclass
class AlterColumnStatement(AlterStatement):
    __slots__ = ("column",)

    column: t.Union[Column, str]

    @property
    def column_name(self) -> str:
        if isinstance(self.column, str):
            return self.column
        elif isinstance(self.column, Column):
            return self.column._meta.name
        else:
            raise ValueError("Unrecognised column type")


@dataclass
class RenameColumn(AlterColumnStatement):
    __slots__ = ("new_name",)

    new_name: str

    @property
    def querystring(self) -> QueryString:
        return QueryString(
            f"RENAME COLUMN {self.column_name} TO {self.new_name}"
        )


@dataclass
class DropColumn(AlterColumnStatement):
    @property
    def querystring(self) -> QueryString:
        return QueryString(f"DROP COLUMN {self.column_name}")


@dataclass
class AddColumn(AlterColumnStatement):
    __slots__ = ("column", "name")

    column: Column
    name: str

    @property
    def querystring(self) -> QueryString:
        self.column._meta.name = self.name
        return QueryString("ADD COLUMN {}", self.column.querystring)


@dataclass
class DropDefault(AlterColumnStatement):
    @property
    def querystring(self) -> QueryString:
        return QueryString(f"ALTER COLUMN {self.column_name} DROP DEFAULT")


@dataclass
class SetColumnType(AlterStatement):
    """
    :param using_expression:
        Postgres can't automatically convert between certain column types. You
        can tell Postgres which action to take. For example
        `my_column_name::integer`.

    """

    old_column: Column
    new_column: Column
    using_expression: t.Optional[str] = None

    @property
    def querystring(self) -> QueryString:
        if self.new_column._meta._table is None:
            self.new_column._meta._table = self.old_column._meta.table

        column_name = self.old_column._meta.name
        query = (
            f"ALTER COLUMN {column_name} TYPE {self.new_column.column_type}"
        )
        if self.using_expression is not None:
            query += f" USING {self.using_expression}"
        return QueryString(query)


@dataclass
class SetDefault(AlterColumnStatement):
    __slots__ = ("column", "value")

    column: Column
    value: t.Any

    @property
    def querystring(self) -> QueryString:
        sql_value = self.column.get_sql_value(self.value)
        return QueryString(
            f"ALTER COLUMN {self.column_name} SET DEFAULT {sql_value}"
        )


@dataclass
class SetUnique(AlterColumnStatement):
    __slots__ = ("boolean",)

    boolean: bool

    @property
    def querystring(self) -> QueryString:
        if self.boolean:
            return QueryString(f"ADD UNIQUE ({self.column_name})")
        else:
            if isinstance(self.column, str):
                raise ValueError(
                    "Removing a unique constraint requires a Column instance "
                    "to be passed as the column arg instead of a string."
                )
            tablename = self.column._meta.table._meta.tablename
            column_name = self.column_name
            key = f"{tablename}_{column_name}_key"
            return QueryString(f'DROP CONSTRAINT "{key}"')


@dataclass
class SetNull(AlterColumnStatement):
    __slots__ = ("boolean",)

    boolean: bool

    @property
    def querystring(self) -> QueryString:
        if self.boolean:
            return QueryString(
                f"ALTER COLUMN {self.column_name} DROP NOT NULL"
            )
        else:
            return QueryString(f"ALTER COLUMN {self.column_name} SET NOT NULL")


@dataclass
class SetLength(AlterColumnStatement):

    __slots__ = ("length",)

    length: int

    @property
    def querystring(self) -> QueryString:
        return QueryString(
            f"ALTER COLUMN {self.column_name} TYPE VARCHAR({self.length})"
        )


@dataclass
class DropConstraint(AlterStatement):
    __slots__ = ("constraint_name",)

    constraint_name: str

    @property
    def querystring(self) -> QueryString:
        return QueryString(
            f"DROP CONSTRAINT IF EXISTS {self.constraint_name}",
        )


@dataclass
class AddForeignKeyConstraint(AlterStatement):
    __slots__ = (
        "constraint_name",
        "foreign_key_column_name",
        "referenced_table_name",
        "on_delete",
        "on_update",
    )

    constraint_name: str
    foreign_key_column_name: str
    referenced_table_name: str
    on_delete: t.Optional[OnDelete]
    on_update: t.Optional[OnUpdate]
    referenced_column_name: str = "id"

    @property
    def querystring(self) -> QueryString:
        query = (
            f"ADD CONSTRAINT {self.constraint_name} FOREIGN KEY "
            f"({self.foreign_key_column_name}) REFERENCES "
            f"{self.referenced_table_name} ({self.referenced_column_name})"
        )
        if self.on_delete:
            query += f" ON DELETE {self.on_delete.value}"
        if self.on_update:
            query += f" ON UPDATE {self.on_update.value}"
        return QueryString(query)


@dataclass
class SetDigits(AlterColumnStatement):

    __slots__ = ("digits", "column_type")

    digits: t.Optional[t.Tuple[int, int]]
    column_type: str

    @property
    def querystring(self) -> QueryString:
        if self.digits is not None:
            precision = self.digits[0]
            scale = self.digits[1]
            return QueryString(
                f"ALTER COLUMN {self.column_name} TYPE "
                f"{self.column_type}({precision}, {scale})"
            )
        else:
            return QueryString(
                f"ALTER COLUMN {self.column_name} TYPE {self.column_type}",
            )


@dataclass
class DropTable:
    tablename: str
    cascade: bool
    if_exists: bool

    @property
    def querystring(self) -> QueryString:
        query = "DROP TABLE"

        if self.if_exists:
            query += " IF EXISTS"

        query += f" {self.tablename}"

        if self.cascade:
            query += " CASCADE"

        return QueryString(query)


class Alter(Query):

    __slots__ = (
        "_add_foreign_key_constraint",
        "_add",
        "_drop_contraint",
        "_drop_default",
        "_drop_table",
        "_drop",
        "_rename_columns",
        "_rename_table",
        "_set_column_type",
        "_set_default",
        "_set_digits",
        "_set_length",
        "_set_null",
        "_set_unique",
    )

    def __init__(self, table: t.Type[Table]):
        super().__init__(table)
        self._add_foreign_key_constraint: t.List[AddForeignKeyConstraint] = []
        self._add: t.List[AddColumn] = []
        self._drop_contraint: t.List[DropConstraint] = []
        self._drop_default: t.List[DropDefault] = []
        self._drop_table: t.Optional[DropTable] = None
        self._drop: t.List[DropColumn] = []
        self._rename_columns: t.List[RenameColumn] = []
        self._rename_table: t.List[RenameTable] = []
        self._set_column_type: t.List[SetColumnType] = []
        self._set_default: t.List[SetDefault] = []
        self._set_digits: t.List[SetDigits] = []
        self._set_length: t.List[SetLength] = []
        self._set_null: t.List[SetNull] = []
        self._set_unique: t.List[SetUnique] = []

    def add_column(self, name: str, column: Column) -> Alter:
        """
        Band.alter().add_column(‘members’, Integer())
        """
        column._meta._table = self.table
        self._add.append(AddColumn(column, name))
        return self

    def drop_column(self, column: t.Union[str, Column]) -> Alter:
        """
        Band.alter().drop_column(Band.popularity)
        """
        self._drop.append(DropColumn(column))
        return self

    def drop_default(self, column: t.Union[str, Column]) -> Alter:
        """
        Band.alter().drop_default(Band.popularity)
        """
        self._drop_default.append(DropDefault(column=column))
        return self

    def drop_table(
        self, cascade: bool = False, if_exists: bool = False
    ) -> Alter:
        """
        Band.alter().drop_table()
        """
        self._drop_table = DropTable(
            tablename=self.table._meta.tablename,
            cascade=cascade,
            if_exists=if_exists,
        )
        return self

    def rename_table(self, new_name: str) -> Alter:
        """
        Band.alter().rename_table('musical_group')
        """
        # We override the existing one rather than appending.
        self._rename_table = [RenameTable(new_name=new_name)]
        return self

    def rename_column(
        self, column: t.Union[str, Column], new_name: str
    ) -> Alter:
        """
        Band.alter().rename_column(Band.popularity, ‘rating’)
        Band.alter().rename_column('popularity', ‘rating’)
        """
        self._rename_columns.append(RenameColumn(column, new_name))
        return self

    def set_column_type(
        self,
        old_column: Column,
        new_column: Column,
        using_expression: t.Optional[str] = None,
    ) -> Alter:
        """
        Change the type of a column.
        """
        self._set_column_type.append(
            SetColumnType(
                old_column=old_column,
                new_column=new_column,
                using_expression=using_expression,
            )
        )
        return self

    def set_default(self, column: Column, value: t.Any) -> Alter:
        """
        Set the default for a column.

        Band.alter().set_default(Band.popularity, 0)
        """
        self._set_default.append(SetDefault(column=column, value=value))
        return self

    def set_null(
        self, column: t.Union[str, Column], boolean: bool = True
    ) -> Alter:
        """
        Band.alter().set_null(Band.name, True)
        Band.alter().set_null('name', True)
        """
        self._set_null.append(SetNull(column, boolean))
        return self

    def set_unique(
        self, column: t.Union[str, Column], boolean: bool = True
    ) -> Alter:
        """
        Band.alter().set_unique(Band.name, True)
        Band.alter().set_unique('name', True)
        """
        self._set_unique.append(SetUnique(column, boolean))
        return self

    def set_length(self, column: t.Union[str, Varchar], length: int) -> Alter:
        """
        Change the max length of a varchar column. Unfortunately, this isn't
        supported by SQLite, but SQLite also doesn't enforce any length limits
        on varchar columns anyway.

        Band.alter().set_length('name', 512)
        """
        if self.engine_type == "sqlite":
            colored_warning(
                (
                    "SQLITE doesn't support changes in length. It also "
                    "doesn't enforce any length limits, so your code will "
                    "still work as expected. Skipping."
                ),
                level=Level.medium,
            )
            return self

        if not isinstance(column, (str, Varchar)):
            raise ValueError(
                "Only Varchar columns can have their length changed."
            )

        self._set_length.append(SetLength(column, length))
        return self

    def _get_constraint_name(self, column: t.Union[str, ForeignKey]) -> str:
        column_name = AlterColumnStatement(column=column).column_name
        tablename = self.table._meta.tablename
        constraint_name = f"{tablename}_{column_name}_fk"
        return constraint_name

    def drop_constraint(self, constraint_name: str) -> Alter:
        self._drop_contraint.append(
            DropConstraint(constraint_name=constraint_name)
        )
        return self

    def drop_foreign_key_constraint(
        self, column: t.Union[str, ForeignKey]
    ) -> Alter:
        constraint_name = self._get_constraint_name(column=column)
        return self.drop_constraint(constraint_name=constraint_name)

    def add_foreign_key_constraint(
        self,
        column: t.Union[str, ForeignKey],
        referenced_table_name: str,
        on_delete: t.Optional[OnDelete] = None,
        on_update: t.Optional[OnUpdate] = None,
        referenced_column_name: str = "id",
    ) -> Alter:
        """
        This will add a new foreign key constraint.

        Band.alter().add_foreign_key_constraint(
            Band.manager,
            referenced_table_name='manager',
            on_delete=OnDelete.cascade
        )
        """
        constraint_name = self._get_constraint_name(column=column)
        column_name = AlterColumnStatement(column=column).column_name

        self._add_foreign_key_constraint.append(
            AddForeignKeyConstraint(
                constraint_name=constraint_name,
                foreign_key_column_name=column_name,
                referenced_table_name=referenced_table_name,
                on_delete=on_delete,
                on_update=on_update,
                referenced_column_name=referenced_column_name,
            )
        )
        return self

    def set_digits(
        self,
        column: t.Union[str, Numeric],
        digits: t.Optional[t.Tuple[int, int]],
    ) -> Alter:
        """
        Alter the precision and scale for a Numeric column.
        """
        column_type = (
            column.__class__.__name__.upper()
            if isinstance(column, Numeric)
            else "NUMERIC"
        )
        self._set_digits.append(
            SetDigits(digits=digits, column=column, column_type=column_type,)
        )
        return self

    @property
    def querystrings(self) -> t.Sequence[QueryString]:
        if self._drop_table is not None:
            return [self._drop_table.querystring]

        query = f"ALTER TABLE {self.table._meta.tablename}"

        alterations = [
            i.querystring
            for i in itertools.chain(
                self._add,
                self._rename_columns,
                self._rename_table,
                self._drop,
                self._drop_default,
                self._set_column_type,
                self._set_unique,
                self._set_null,
                self._set_length,
                self._set_default,
                self._set_digits,
            )
        ]

        if self.engine_type == "sqlite":
            # Can only perform one alter statement at a time.
            query += " {}"
            return [QueryString(query, i) for i in alterations]

        # Postgres can perform them all at once:
        query += ",".join([" {}" for i in alterations])

        return [QueryString(query, *alterations)]
