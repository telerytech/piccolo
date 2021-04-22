from __future__ import annotations

import typing as t
from dataclasses import dataclass, field

from piccolo.apps.migrations.auto.diffable_table import DiffableTable
from piccolo.apps.migrations.auto.migration_manager import MigrationManager


@dataclass
class SchemaSnapshot:
    """
    Adds up a sequence of MigrationManagers, and returns a snapshot of what
    the schema looks like.
    """

    # In ascending order of date created.
    managers: t.List[MigrationManager] = field(default_factory=list)

    ###########################################################################

    def get_table_from_snapshot(self, table_class_name: str) -> DiffableTable:
        snapshot = self.get_snapshot()
        filtered = [i for i in snapshot if i.class_name == table_class_name]
        if len(filtered) == 0:
            raise ValueError(f"No match was found for {table_class_name}")
        return filtered[0]

    ###########################################################################

    def get_snapshot(self) -> t.List[DiffableTable]:
        tables: t.List[DiffableTable] = []

        # Make sure the managers are sorted correctly:
        sorted_managers = sorted(self.managers, key=lambda x: x.migration_id)

        for manager in sorted_managers:
            for table in manager.add_tables:
                tables.append(table)

            for drop_table in manager.drop_tables:
                tables = [
                    i for i in tables if i.class_name != drop_table.class_name
                ]

            for rename_table in manager.rename_tables:
                for table in tables:
                    if table.class_name == rename_table.old_class_name:
                        table.class_name = rename_table.new_class_name
                        table.tablename = rename_table.new_tablename
                        break

            for table in tables:
                add_columns = manager.add_columns.columns_for_table_class_name(
                    table.class_name
                )
                table.columns.extend(add_columns)

                ###############################################################

                drop_columns = manager.drop_columns.for_table_class_name(
                    table.class_name
                )
                for drop_column in drop_columns:
                    table.columns = [
                        i
                        for i in table.columns
                        if i._meta.name != drop_column.column_name
                    ]

                ###############################################################

                alter_columns = manager.alter_columns.for_table_class_name(
                    table.class_name
                )
                for alter_column in alter_columns:
                    for index, column in enumerate(table.columns):
                        if column._meta.name == alter_column.column_name:
                            for key, value in alter_column.params.items():
                                setattr(column._meta, key, value)
                                column._meta.params.update({key: value})

                            # If the column type has changed, we need to update
                            # it.
                            if (
                                alter_column.column_class
                                != alter_column.old_column_class
                            ):
                                if alter_column.column_class is not None:
                                    new_column = alter_column.column_class(
                                        **column._meta.params
                                    )
                                    new_column._meta = column._meta
                                    table.columns[index] = new_column

                ###############################################################

                for (
                    rename_column
                ) in manager.rename_columns.for_table_class_name(
                    table.class_name
                ):
                    for column in table.columns:
                        if column._meta.name == rename_column.old_column_name:
                            column._meta.name = rename_column.new_column_name

        return tables
