import os
import sys

from targ import CLI  # type: ignore

from piccolo.apps.app.piccolo_app import APP_CONFIG as app_config
from piccolo.apps.asgi.piccolo_app import APP_CONFIG as asgi_config
from piccolo.apps.meta.piccolo_app import APP_CONFIG as meta_config
from piccolo.apps.migrations.piccolo_app import APP_CONFIG as migrations_config
from piccolo.apps.playground.piccolo_app import APP_CONFIG as playground_config
from piccolo.apps.project.piccolo_app import APP_CONFIG as project_config
from piccolo.apps.shell.piccolo_app import APP_CONFIG as shell_config
from piccolo.apps.sql_shell.piccolo_app import APP_CONFIG as sql_shell_config
from piccolo.apps.user.piccolo_app import APP_CONFIG as user_config
from piccolo.conf.apps import AppRegistry, Finder

DIAGNOSE_FLAG = "--diagnose"


def get_diagnose_flag() -> bool:
    return DIAGNOSE_FLAG in sys.argv


def main():
    """
    The entrypoint to the Piccolo CLI.
    """
    # In case it's run from an entrypoint:
    sys.path.insert(0, os.getcwd())

    ###########################################################################
    # Run in diagnose mode if requested.

    diagnose = get_diagnose_flag()
    if diagnose:
        print("Diagnosis...")
        if Finder(diagnose=True).get_app_registry():
            print("Everything OK")
        return

    ###########################################################################

    cli = CLI(description="Piccolo CLI")

    ###########################################################################
    # Register the base apps.

    for _app_config in [
        app_config,
        asgi_config,
        meta_config,
        migrations_config,
        playground_config,
        project_config,
        shell_config,
        sql_shell_config,
        user_config,
    ]:
        for command in _app_config.commands:
            cli.register(command, group_name=_app_config.app_name)

    ###########################################################################
    # Get user defined apps.

    try:
        APP_REGISTRY: AppRegistry = Finder().get_app_registry()
    except (ImportError, AttributeError):
        print(
            "Can't import the APP_REGISTRY from piccolo_conf - some "
            "commands may be missing. If this is a new project don't worry. "
            f"To see a full traceback use `piccolo {DIAGNOSE_FLAG}`"
        )
    else:
        for app_name, _app_config in APP_REGISTRY.app_configs.items():
            for command in _app_config.commands:
                if cli.command_exists(
                    group_name=app_name, command_name=command.__name__
                ):
                    # Skipping - already registered.
                    continue
                cli.register(command, group_name=app_name)

    ###########################################################################

    cli.run()


if __name__ == "__main__":
    main()
