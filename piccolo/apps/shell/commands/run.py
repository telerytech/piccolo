import sys
import typing as t

from piccolo.conf.apps import AppConfig, AppRegistry, Finder
from piccolo.table import Table

try:
    import IPython  # type: ignore
    from IPython.core.interactiveshell import _asyncio_runner  # type: ignore

    IPYTHON = True
except ImportError:
    IPYTHON = False


def start_ipython_shell(
    **tables: t.Dict[str, t.Type[Table]]
):  # pragma: no cover
    if not IPYTHON:
        sys.exit(
            "Install iPython using `pip install ipython` to use this feature."
        )

    existing_global_names = globals().keys()
    for table_class_name, table_class in tables.items():
        if table_class_name not in existing_global_names:
            globals()[table_class_name] = table_class

    IPython.embed(using=_asyncio_runner, colors="neutral")


def run():
    """
    Runs an iPython shell, and automatically imports all of the Table classes
    from your project.
    """
    app_registry: AppRegistry = Finder().get_app_registry()

    tables = {}
    spacer = "-------"

    if app_registry.app_configs:
        print(spacer)

        for app_name, app_config in app_registry.app_configs.items():
            app_config: AppConfig = app_config
            print(f"Importing {app_name} tables:")
            if app_config.table_classes:
                for table_class in sorted(
                    app_config.table_classes, key=lambda x: x.__name__
                ):
                    table_class_name = table_class.__name__
                    print(f"- {table_class_name}")
                    tables[table_class_name] = table_class
            else:
                print("- None")

        print(spacer)

    start_ipython_shell(**tables)
