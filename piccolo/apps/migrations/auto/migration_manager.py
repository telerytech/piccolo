from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass, field

from piccolo.apps.migrations.auto.diffable_table import DiffableTable
from piccolo.apps.migrations.auto.operations import (AlterColumn, DropColumn,
                                                     RenameColumn, RenameTable)
from piccolo.apps.migrations.auto.serialisation import deserialise_params
from piccolo.columns import Column, column_types
from piccolo.engine import engine_finder
from piccolo.table import Table


@dataclass
class AddColumnClass:
    column: Column
    table_class_name: str
    tablename: str


@dataclass
class AddColumnCollection:
    add_columns: t.List[AddColumnClass] = field(default_factory=list)

    def append(self, add_column: AddColumnClass):
        self.add_columns.append(add_column)

    def for_table_class_name(
        self, table_class_name: str
    ) -> t.List[AddColumnClass]:
        return [
            i
            for i in self.add_columns
            if i.table_class_name == table_class_name
        ]

    def columns_for_table_class_name(
        self, table_class_name: str
    ) -> t.List[Column]:
        return [
            i.column
            for i in self.add_columns
            if i.table_class_name == table_class_name
        ]

    @property
    def table_class_names(self) -> t.List[str]:
        return list(set([i.table_class_name for i in self.add_columns]))


@dataclass
class DropColumnCollection:
    drop_columns: t.List[DropColumn] = field(default_factory=list)

    def append(self, drop_column: DropColumn):
        self.drop_columns.append(drop_column)

    def for_table_class_name(
        self, table_class_name: str
    ) -> t.List[DropColumn]:
        return [
            i
            for i in self.drop_columns
            if i.table_class_name == table_class_name
        ]

    @property
    def table_class_names(self) -> t.List[str]:
        return list(set([i.table_class_name for i in self.drop_columns]))


@dataclass
class RenameColumnCollection:
    rename_columns: t.List[RenameColumn] = field(default_factory=list)

    def append(self, rename_column: RenameColumn):
        self.rename_columns.append(rename_column)

    def for_table_class_name(
        self, table_class_name: str
    ) -> t.List[RenameColumn]:
        return [
            i
            for i in self.rename_columns
            if i.table_class_name == table_class_name
        ]

    @property
    def table_class_names(self) -> t.List[str]:
        return list(set([i.table_class_name for i in self.rename_columns]))


@dataclass
class AlterColumnCollection:
    alter_columns: t.List[AlterColumn] = field(default_factory=list)

    def append(self, alter_column: AlterColumn):
        self.alter_columns.append(alter_column)

    def for_table_class_name(
        self, table_class_name: str
    ) -> t.List[AlterColumn]:
        return [
            i
            for i in self.alter_columns
            if i.table_class_name == table_class_name
        ]

    @property
    def table_class_names(self) -> t.List[str]:
        return list(set([i.table_class_name for i in self.alter_columns]))


@dataclass
class MigrationManager:
    """
    Each auto generated migration returns a MigrationManager. It contains
    all of the schema changes that migration wants to make.
    """

    migration_id: str = ""
    app_name: str = ""
    add_tables: t.List[DiffableTable] = field(default_factory=list)
    drop_tables: t.List[DiffableTable] = field(default_factory=list)
    rename_tables: t.List[RenameTable] = field(default_factory=list)
    add_columns: AddColumnCollection = field(
        default_factory=AddColumnCollection
    )
    drop_columns: DropColumnCollection = field(
        default_factory=DropColumnCollection
    )
    rename_columns: RenameColumnCollection = field(
        default_factory=RenameColumnCollection
    )
    alter_columns: AlterColumnCollection = field(
        default_factory=AlterColumnCollection
    )
    raw: t.List[t.Union[t.Callable, t.Coroutine]] = field(default_factory=list)
    raw_backwards: t.List[t.Union[t.Callable, t.Coroutine]] = field(
        default_factory=list
    )

    def add_table(
        self,
        class_name: str,
        tablename: str,
        columns: t.Optional[t.List[Column]] = None,
    ):
        if not columns:
            columns = []

        self.add_tables.append(
            DiffableTable(
                class_name=class_name, tablename=tablename, columns=columns
            )
        )

    def drop_table(self, class_name: str, tablename: str):
        self.drop_tables.append(
            DiffableTable(class_name=class_name, tablename=tablename)
        )

    def rename_table(
        self,
        old_class_name: str,
        old_tablename: str,
        new_class_name: str,
        new_tablename: str,
    ):
        self.rename_tables.append(
            RenameTable(
                old_class_name=old_class_name,
                old_tablename=old_tablename,
                new_class_name=new_class_name,
                new_tablename=new_tablename,
            )
        )

    def add_column(
        self,
        table_class_name: str,
        tablename: str,
        column_name: str,
        column_class_name: str = "",
        column_class: t.Optional[t.Type[Column]] = None,
        params: t.Dict[str, t.Any] = {},
    ):
        """
        Add a new column to the table.

        :param column_class_name:
            The column type was traditionally specified as a string, using this
            variable. This didn't allow users to define custom column types
            though, which is why newer migrations directly reference a
            ``Column`` subclass using ``column_class``.
        :param column_class:
            A direct reference to a ``Column`` subclass.

        """
        column_class = column_class or getattr(column_types, column_class_name)

        if column_class is None:
            raise ValueError("Unrecognised column type")

        cleaned_params = deserialise_params(params=params)
        column = column_class(**cleaned_params)
        column._meta.name = column_name
        self.add_columns.append(
            AddColumnClass(
                column=column,
                tablename=tablename,
                table_class_name=table_class_name,
            )
        )

    def drop_column(
        self, table_class_name: str, tablename: str, column_name: str
    ):
        self.drop_columns.append(
            DropColumn(
                table_class_name=table_class_name,
                column_name=column_name,
                tablename=tablename,
            )
        )

    def rename_column(
        self,
        table_class_name: str,
        tablename: str,
        old_column_name: str,
        new_column_name: str,
    ):
        self.rename_columns.append(
            RenameColumn(
                table_class_name=table_class_name,
                tablename=tablename,
                old_column_name=old_column_name,
                new_column_name=new_column_name,
            )
        )

    def alter_column(
        self,
        table_class_name: str,
        tablename: str,
        column_name: str,
        params: t.Dict[str, t.Any],
        old_params: t.Dict[str, t.Any],
        column_class: t.Optional[t.Type[Column]] = None,
        old_column_class: t.Optional[t.Type[Column]] = None,
    ):
        """
        All possible alterations aren't currently supported.
        """
        self.alter_columns.append(
            AlterColumn(
                table_class_name=table_class_name,
                tablename=tablename,
                column_name=column_name,
                params=params,
                old_params=old_params,
                column_class=column_class,
                old_column_class=old_column_class,
            )
        )

    def add_raw(self, raw: t.Union[t.Callable, t.Coroutine]):
        """
        A migration manager can execute arbitrary functions or coroutines when
        run. This is useful if you want to execute raw SQL.
        """
        self.raw.append(raw)

    def add_raw_backwards(self, raw: t.Union[t.Callable, t.Coroutine]):
        """
        When reversing a migration, you may want to run extra code to help
        clean up.
        """
        self.raw_backwards.append(raw)

    ###########################################################################

    async def get_table_from_snaphot(
        self,
        table_class_name: str,
        app_name: t.Optional[str],
        offset: int = 0,
        migration_id: t.Optional[str] = None,
    ) -> t.Type[Table]:
        """
        Returns a Table subclass which can be used for modifying data within
        a migration.

        :param offset:
            Lets you get a table as it appeared in an older migration. If the
            offset is -1, the table will come from the previous migration.

        """
        from piccolo.apps.migrations.commands.base import BaseMigrationManager

        if migration_id is None:
            migration_id = self.migration_id

        if app_name is None:
            app_name = self.app_name

        diffable_table = await BaseMigrationManager().get_table_from_snaphot(
            app_name=app_name,
            table_class_name=table_class_name,
            max_migration_id=migration_id,
            offset=offset,
        )
        return diffable_table.to_table_class()

    ###########################################################################

    async def _run_alter_columns(self, backwards=False):
        for table_class_name in self.alter_columns.table_class_names:
            alter_columns = self.alter_columns.for_table_class_name(
                table_class_name
            )

            if not alter_columns:
                continue

            _Table: t.Type[Table] = type(table_class_name, (Table,), {})
            _Table._meta.tablename = alter_columns[0].tablename

            for alter_column in alter_columns:

                params = (
                    alter_column.old_params
                    if backwards
                    else alter_column.params
                )

                old_params = (
                    alter_column.params
                    if backwards
                    else alter_column.old_params
                )

                ###############################################################

                # Change the column type if possible
                column_class = (
                    alter_column.old_column_class
                    if backwards
                    else alter_column.column_class
                )
                old_column_class = (
                    alter_column.column_class
                    if backwards
                    else alter_column.old_column_class
                )

                if (old_column_class is not None) and (
                    column_class is not None
                ):
                    if old_column_class != column_class:
                        old_column = old_column_class(**old_params)
                        old_column._meta._table = _Table
                        old_column._meta._name = alter_column.column_name

                        new_column = column_class(**params)
                        new_column._meta._table = _Table
                        new_column._meta._name = alter_column.column_name

                        await _Table.alter().set_column_type(
                            old_column=old_column, new_column=new_column
                        )

                ###############################################################

                column_name = alter_column.column_name

                null = params.get("null")
                if null is not None:
                    await _Table.alter().set_null(
                        column=column_name, boolean=null
                    ).run()

                length = params.get("length")
                if length is not None:
                    await _Table.alter().set_length(
                        column=column_name, length=length
                    ).run()

                unique = params.get("unique")
                if unique is not None:
                    # When modifying unique contraints, we need to pass in
                    # a column type, and not just the column name.
                    column = Column()
                    column._meta._table = _Table
                    column._meta._name = column_name
                    await _Table.alter().set_unique(
                        column=column, boolean=unique
                    ).run()

                index = params.get("index")
                index_method = params.get("index_method")
                if index is None:
                    if index_method is not None:
                        # If the index value hasn't changed, but the
                        # index_method value has, this indicates we need
                        # to change the index type.
                        column = Column()
                        column._meta._table = _Table
                        column._meta._name = column_name
                        await _Table.drop_index([column]).run()
                        await _Table.create_index(
                            [column], method=index_method, if_not_exists=True
                        ).run()
                else:
                    # If the index value has changed, then we are either
                    # dropping, or creating an index.
                    column = Column()
                    column._meta._table = _Table
                    column._meta._name = column_name
                    if index is True:
                        kwargs = (
                            {"method": index_method} if index_method else {}
                        )
                        await _Table.create_index(
                            [column], if_not_exists=True, **kwargs
                        ).run()
                    else:
                        await _Table.drop_index([column]).run()

                # None is a valid value, so retrieve ellipsis if not found.
                default = params.get("default", ...)
                if default is not ...:
                    column = Column()
                    column._meta._table = _Table
                    column._meta._name = column_name
                    if default is None:
                        await _Table.alter().drop_default(column=column).run()
                    else:
                        column.default = default
                        await _Table.alter().set_default(
                            column=column, value=column.get_default_value()
                        ).run()

                # None is a valid value, so retrieve ellipsis if not found.
                digits = params.get("digits", ...)
                if digits is not ...:
                    await _Table.alter().set_digits(
                        column=alter_column.column_name, digits=digits,
                    ).run()

    async def _run_drop_tables(self, backwards=False):
        if backwards:
            for diffable_table in self.drop_tables:
                _Table = await self.get_table_from_snaphot(
                    table_class_name=diffable_table.class_name,
                    app_name=self.app_name,
                    offset=-1,
                )
                await _Table.create_table().run()
        else:
            for diffable_table in self.drop_tables:
                await (
                    diffable_table.to_table_class().alter().drop_table().run()
                )

    async def _run_drop_columns(self, backwards=False):
        if backwards:
            for drop_column in self.drop_columns.drop_columns:
                _Table = await self.get_table_from_snaphot(
                    table_class_name=drop_column.table_class_name,
                    app_name=self.app_name,
                    offset=-1,
                )
                column_to_restore = _Table._meta.get_column_by_name(
                    drop_column.column_name
                )
                await _Table.alter().add_column(
                    name=drop_column.column_name, column=column_to_restore
                ).run()
        else:
            for table_class_name in self.drop_columns.table_class_names:
                columns = self.drop_columns.for_table_class_name(
                    table_class_name
                )

                if not columns:
                    continue

                _Table: t.Type[Table] = type(table_class_name, (Table,), {})
                _Table._meta.tablename = columns[0].tablename

                for column in columns:
                    await _Table.alter().drop_column(
                        column=column.column_name
                    ).run()

    async def _run_rename_tables(self, backwards=False):
        for rename_table in self.rename_tables:
            class_name = (
                rename_table.new_class_name
                if backwards
                else rename_table.old_class_name
            )
            tablename = (
                rename_table.new_tablename
                if backwards
                else rename_table.old_tablename
            )
            new_tablename = (
                rename_table.old_tablename
                if backwards
                else rename_table.new_tablename
            )

            _Table: t.Type[Table] = type(class_name, (Table,), {})
            _Table._meta.tablename = tablename

            await _Table.alter().rename_table(new_name=new_tablename).run()

    async def _run_rename_columns(self, backwards=False):
        for table_class_name in self.rename_columns.table_class_names:
            columns = self.rename_columns.for_table_class_name(
                table_class_name
            )

            if not columns:
                continue

            _Table: t.Type[Table] = type(table_class_name, (Table,), {})
            _Table._meta.tablename = columns[0].tablename

            for rename_column in columns:
                column = (
                    rename_column.new_column_name
                    if backwards
                    else rename_column.old_column_name
                )
                new_name = (
                    rename_column.old_column_name
                    if backwards
                    else rename_column.new_column_name
                )

                await _Table.alter().rename_column(
                    column=column, new_name=new_name,
                ).run()

    async def _run_add_tables(self, backwards=False):
        if backwards:
            for add_table in self.add_tables:
                await add_table.to_table_class().alter().drop_table(
                    cascade=True
                ).run()
        else:
            for add_table in self.add_tables:
                _Table: t.Type[Table] = type(
                    add_table.class_name,
                    (Table,),
                    {
                        column._meta.name: column
                        for column in add_table.columns
                    },
                )
                _Table._meta.tablename = add_table.tablename

                await _Table.create_table().run()

    async def _run_add_columns(self, backwards=False):
        """
        Add columns, which belong to new and existing tables
        """
        if backwards:
            for add_column in self.add_columns.add_columns:
                if add_column.table_class_name in [
                    i.class_name for i in self.add_tables
                ]:
                    # Don't reverse the add column as the table is going to
                    # be deleted.
                    continue

                _Table: t.Type[Table] = type(
                    add_column.table_class_name, (Table,), {}
                )
                _Table._meta.tablename = add_column.tablename

                await _Table.alter().drop_column(add_column.column).run()
        else:
            for table_class_name in self.add_columns.table_class_names:
                add_columns: t.List[
                    AddColumnClass
                ] = self.add_columns.for_table_class_name(table_class_name)

                # Define the table, with the columns, so the metaclass
                # sets up the columns correctly.
                _Table: t.Type[Table] = type(
                    add_columns[0].table_class_name,
                    (Table,),
                    {
                        add_column.column._meta.name: add_column.column
                        for add_column in add_columns
                    },
                )
                _Table._meta.tablename = add_columns[0].tablename

                for add_column in add_columns:
                    column = add_column.column
                    await _Table.alter().add_column(
                        name=column._meta.name, column=column
                    ).run()
                    if add_column.column._meta.index:
                        await _Table.create_index([add_column.column]).run()

    async def run(self):
        print("Running MigrationManager ...")

        engine = engine_finder()

        if not engine:
            raise Exception("Can't find engine")

        async with engine.transaction():

            for raw in self.raw:
                if inspect.iscoroutinefunction(raw):
                    await raw()
                else:
                    raw()

            await self._run_add_tables()
            await self._run_rename_tables()
            await self._run_add_columns()
            await self._run_drop_columns()
            await self._run_drop_tables()
            await self._run_rename_columns()
            await self._run_alter_columns()

    async def run_backwards(self):
        print("Reversing MigrationManager ...")

        engine = engine_finder()

        if not engine:
            raise Exception("Can't find engine")

        async with engine.transaction():

            for raw in self.raw_backwards:
                if inspect.iscoroutinefunction(raw):
                    await raw()
                else:
                    raw()

            await self._run_add_columns(backwards=True)
            await self._run_add_tables(backwards=True)
            await self._run_drop_tables(backwards=True)
            await self._run_rename_tables(backwards=True)
            await self._run_drop_columns(backwards=True)
            await self._run_rename_columns(backwards=True)
            await self._run_alter_columns(backwards=True)
