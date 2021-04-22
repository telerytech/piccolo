from __future__ import annotations

import sys
import typing as t

from piccolo.apps.migrations.auto import MigrationManager
from piccolo.apps.migrations.commands.base import BaseMigrationManager
from piccolo.apps.migrations.tables import Migration
from piccolo.conf.apps import AppConfig, MigrationModule


class ForwardsMigrationManager(BaseMigrationManager):
    def __init__(
        self,
        app_name: str,
        migration_id: str,
        fake: bool = False,
        *args,
        **kwargs,
    ):
        self.app_name = app_name
        self.migration_id = migration_id
        self.fake = fake
        super().__init__()

    async def run_migrations(self, app_config: AppConfig) -> None:
        already_ran = await Migration.get_migrations_which_ran(
            app_name=self.app_name
        )

        migration_modules: t.Dict[
            str, MigrationModule
        ] = self.get_migration_modules(app_config.migrations_folder_path)

        ids = self.get_migration_ids(migration_modules)
        print(f"All migration ids = {ids}")

        havent_run = sorted(set(ids) - set(already_ran))
        print(f"Haven't run = {havent_run}")

        if len(havent_run) == 0:
            # Make sure a status of 0 is returned, as we don't want this
            # to appear as an error in automated scripts.
            print("No migrations left to run!")
            sys.exit(0)

        if self.migration_id == "all":
            subset = havent_run
        elif self.migration_id == "1":
            subset = havent_run[:1]
        else:
            try:
                index = havent_run.index(self.migration_id)
            except ValueError:
                sys.exit(f"{self.migration_id} is unrecognised")
            else:
                subset = havent_run[: index + 1]

        for _id in subset:
            if self.fake:
                print(f"Faked {_id}")
            else:
                migration_module = migration_modules[_id]
                response = await migration_module.forwards()

                if isinstance(response, MigrationManager):
                    await response.run()

                print(f"-> Ran {_id}")

            await Migration.insert().add(
                Migration(name=_id, app_name=self.app_name)
            ).run()

    async def run(self):
        print("Running migrations ...")
        await self.create_migration_table()

        app_config = self.get_app_config(app_name=self.app_name)

        await self.run_migrations(app_config)


async def forwards(
    app_name: str, migration_id: str = "all", fake: bool = False
):
    """
    Runs any migrations which haven't been run yet.

    :param app_name:
        The name of the app to migrate. Specify a value of 'all' to run
        migrations for all apps.
    :param migration_id:
        Migrations will be ran up to and including this migration_id.
        Specify a value of 'all' to run all of the migrations. Specify a
        value of '1' to just run the next migration.
    :param fake:
        If set, will record the migrations as being run without actually
        running them.
    """
    if app_name == "all":
        sorted_app_names = BaseMigrationManager().get_sorted_app_names()
        for _app_name in sorted_app_names:
            print(f"\nMigrating {_app_name}")
            print("------------------------------------------------")
            manager = ForwardsMigrationManager(
                app_name=_app_name, migration_id="all", fake=fake
            )
            await manager.run()
    else:
        manager = ForwardsMigrationManager(
            app_name=app_name, migration_id=migration_id, fake=fake
        )
        await manager.run()
