from __future__ import annotations

import datetime
import os
import sys
import typing as t
from itertools import chain
from types import ModuleType

import black  # type: ignore
import jinja2

from piccolo import __VERSION__
from piccolo.apps.migrations.auto import (AlterStatements, DiffableTable,
                                          SchemaDiffer, SchemaSnapshot)
from piccolo.conf.apps import AppConfig, Finder
from piccolo.engine import SQLiteEngine

from .base import BaseMigrationManager

TEMPLATE_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates"
)

JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIRECTORY),
)


MIGRATION_MODULES: t.Dict[str, ModuleType] = {}


def render_template(**kwargs):
    template = JINJA_ENV.get_template("migration.py.jinja")
    return template.render(version=__VERSION__, **kwargs)


def _create_migrations_folder(migrations_path: str) -> bool:
    """
    Creates the folder that migrations live in. Returns True/False depending
    on whether it was created or not.
    """
    if os.path.exists(migrations_path):
        return False
    else:
        os.mkdir(migrations_path)
        with open(os.path.join(migrations_path, "__init__.py"), "w"):
            pass
        return True


async def _create_new_migration(app_config: AppConfig, auto=False) -> None:
    """
    Creates a new migration file on disk.
    """
    _id = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Originally we just used the _id as the filename, but colons aren't
    # supported in Windows, so we need to sanitize it. We don't want to
    # change the _id format though, as it would break existing migrations.
    # The filename doesn't have any special significance - only the id matters.
    filename = _id.replace(":", "-")

    path = os.path.join(app_config.migrations_folder_path, f"{filename}.py")

    if auto:
        alter_statements = await AutoMigrationManager().get_alter_statements(
            app_config=app_config
        )

        _alter_statements = list(
            chain(*[i.statements for i in alter_statements])
        )
        extra_imports = sorted(
            list(set(chain(*[i.extra_imports for i in alter_statements])))
        )
        extra_definitions = sorted(
            list(set(chain(*[i.extra_definitions for i in alter_statements])))
        )

        if sum([len(i.statements) for i in alter_statements]) == 0:
            print("No changes detected - exiting.")
            sys.exit(0)

        file_contents = render_template(
            migration_id=_id,
            auto=True,
            alter_statements=_alter_statements,
            extra_imports=extra_imports,
            extra_definitions=extra_definitions,
            app_name=app_config.app_name,
        )
    else:
        file_contents = render_template(migration_id=_id, auto=False)

    # Beautify the file contents a bit.
    file_contents = black.format_str(
        file_contents, mode=black.FileMode(line_length=82)
    )

    with open(path, "w") as f:
        f.write(file_contents)


###############################################################################


class AutoMigrationManager(BaseMigrationManager):
    async def get_alter_statements(
        self, app_config: AppConfig
    ) -> t.List[AlterStatements]:
        """
        Works out which alter statements are required.
        """
        migration_managers = await self.get_migration_managers(
            app_name=app_config.app_name
        )

        schema_snapshot = SchemaSnapshot(migration_managers)
        snapshot = schema_snapshot.get_snapshot()

        # Now get the current schema:
        current_diffable_tables = [
            DiffableTable(
                class_name=i.__name__,
                tablename=i._meta.tablename,
                columns=i._meta.non_default_columns,
            )
            for i in app_config.table_classes
        ]

        # Compare the current schema with the snapshot
        differ = SchemaDiffer(
            schema=current_diffable_tables, schema_snapshot=snapshot
        )
        alter_statements = differ.get_alter_statements()

        return alter_statements


###############################################################################


async def new(app_name: str, auto: bool = False):
    """
    Creates a new migration file in the migrations folder.

    :param app_name:
        The app to create a migration for.
    :param auto:
        Auto create the migration contents.

    """
    print("Creating new migration ...")

    engine = Finder().get_engine()
    if auto and isinstance(engine, SQLiteEngine):
        sys.exit("Auto migrations aren't currently supported by SQLite.")

    app_config = Finder().get_app_config(app_name=app_name)

    _create_migrations_folder(app_config.migrations_folder_path)
    await _create_new_migration(app_config=app_config, auto=auto)
