from piccolo.conf.apps import AppConfig

from .commands.run import run

APP_CONFIG = AppConfig(
    app_name="playground", migrations_folder_path="", commands=[run]
)
