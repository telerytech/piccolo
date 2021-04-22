from piccolo.conf.apps import AppConfig

from .commands.version import version

APP_CONFIG = AppConfig(
    app_name="meta", migrations_folder_path="", commands=[version]
)
