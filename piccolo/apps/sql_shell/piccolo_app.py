from piccolo.conf.apps import AppConfig

from .commands.run import run

APP_CONFIG = AppConfig(
    app_name="sql_shell", migrations_folder_path="", commands=[run]
)
