import os

from piccolo.conf.apps import AppConfig

from .commands.change_password import change_password
from .commands.create import create
from .tables import BaseUser

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


APP_CONFIG = AppConfig(
    app_name="user",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY, "piccolo_migrations"
    ),
    table_classes=[BaseUser],
    migration_dependencies=[],
    commands=[create, change_password],
)
