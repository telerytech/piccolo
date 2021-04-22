from __future__ import annotations

import typing as t

from piccolo.apps.migrations.commands.base import BaseMigrationManager
from piccolo.apps.migrations.tables import Migration


class CleanMigrationManager(BaseMigrationManager):
    def __init__(self, app_name: str, auto_agree: bool = False):
        self.app_name = app_name
        self.auto_agree = auto_agree
        super().__init__()

    def get_migration_ids_to_remove(self) -> t.List[str]:
        """
        Returns a list of migration ID strings, which are rows in the table,
        but don't have a corresponding migration module on disk.
        """
        app_config = self.get_app_config(app_name=self.app_name)

        migration_module_dict = self.get_migration_modules(
            folder_path=app_config.migrations_folder_path
        )

        # The migration IDs which are in migration modules.
        migration_ids = self.get_migration_ids(
            migration_module_dict=migration_module_dict
        )

        query = (
            Migration.select(Migration.name)
            .where(Migration.app_name == self.app_name)
            .output(as_list=True)
        )

        if len(migration_ids) > 0:
            query = query.where(Migration.name.not_in(migration_ids))

        migration_ids_to_remove = query.run_sync()
        return migration_ids_to_remove

    async def run(self):
        print("Checking the migration table ...")

        # Make sure the migration table exists, otherwise we'll get an error.
        await self.create_migration_table()

        migration_ids_to_remove = self.get_migration_ids_to_remove()

        if migration_ids_to_remove:
            id_string = "\n".join(migration_ids_to_remove)
            print(
                "The following migrations exist in the table, not not in "
                "modules:"
            )
            print(id_string)
            confirm = (
                "y"
                if self.auto_agree
                else input("Would you like to delete these rows? (y/N)")
            )
            if confirm == "y":
                await Migration.delete().where(
                    Migration.name.is_in(migration_ids_to_remove)
                ).run()
                print("Deleted")
            else:
                print("Cancelled")
        else:
            print(
                "No migrations exist in the table, which aren't also in "
                "modules."
            )


async def clean(app_name: str, auto_agree: bool = False):
    """
    Identifies any rows in the migration table which have no corresponding
    migration module on disk, and then optionally deletes those rows.

    :param app_name:
        The name of the app to check.
    :param auto_agree:
        If true, automatically agree to any input prompts.

    """
    await CleanMigrationManager(app_name=app_name, auto_agree=auto_agree).run()
