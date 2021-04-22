from __future__ import annotations

import importlib
import os
import sys
import typing as t

from piccolo.apps.migrations.auto.diffable_table import DiffableTable
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.apps.migrations.auto.schema_snapshot import SchemaSnapshot
from piccolo.apps.migrations.tables import Migration
from piccolo.conf.apps import Finder, MigrationModule


class BaseMigrationManager(Finder):
    async def create_migration_table(self) -> bool:
        """
        Creates the migration table in the database. Returns True/False
        depending on whether it was created or not.
        """
        if not await Migration.table_exists().run():
            await Migration.create_table().run()
            return True
        return False

    def get_migration_modules(
        self, folder_path: str
    ) -> t.Dict[str, MigrationModule]:
        """
        Imports the migration modules in the given folder path, and returns
        a mapping of migration ID to the corresponding migration module.

        """
        migration_modules = {}

        sys.path.insert(0, folder_path)

        folder_contents = os.listdir(folder_path)
        excluded = ("__init__.py",)
        migration_names = [
            i.split(".py")[0]
            for i in folder_contents
            if ((i not in excluded) and i.endswith(".py"))
        ]

        modules: t.List[MigrationModule] = [
            t.cast(MigrationModule, importlib.import_module(name))
            for name in migration_names
        ]
        for m in modules:
            _id = getattr(m, "ID", None)
            if _id:
                migration_modules[_id] = m

        return migration_modules

    def get_migration_ids(
        self, migration_module_dict: t.Dict[str, MigrationModule]
    ) -> t.List[str]:
        """
        Returns a list of migration IDs, from the Python migration files.
        """
        return sorted(list(migration_module_dict.keys()))

    async def get_migration_managers(
        self,
        app_name: str,
        max_migration_id: t.Optional[str] = None,
        offset: int = 0,
    ) -> t.List[MigrationManager]:
        """
        Call the forwards coroutine in each migration module. Each one should
        return a `MigrationManger`. Combine all of the results, and return in
        a list.

        :param max_migration_id:
            If set, only MigrationManagers up to and including the given
            migration ID will be returned.
        """
        migration_managers: t.List[MigrationManager] = []

        app_config = self.get_app_config(app_name=app_name)

        migrations_folder = app_config.migrations_folder_path

        migration_modules: t.Dict[
            str, MigrationModule
        ] = self.get_migration_modules(migrations_folder)

        migration_ids = sorted(migration_modules.keys())

        for migration_id in migration_ids:
            migration_module = migration_modules[migration_id]
            response = await migration_module.forwards()
            if isinstance(response, MigrationManager):
                migration_managers.append(response)
                if (
                    max_migration_id
                    and response.migration_id == max_migration_id
                ):
                    break

        if offset > 0:
            raise Exception(
                "Positive offset values aren't currently supported"
            )
        elif offset < 0:
            return migration_managers[0:offset]
        else:
            return migration_managers

    async def get_table_from_snaphot(
        self,
        app_name: str,
        table_class_name: str,
        max_migration_id: t.Optional[str] = None,
        offset: int = 0,
    ) -> DiffableTable:
        """
        This will generate a SchemaSnapshot up to the given migration ID, and
        will return a DiffableTable class from that snapshot.
        """
        migration_managers = await self.get_migration_managers(
            app_name=app_name, max_migration_id=max_migration_id, offset=offset
        )
        schema_snapshot = SchemaSnapshot(managers=migration_managers)

        return schema_snapshot.get_table_from_snapshot(
            table_class_name=table_class_name
        )
