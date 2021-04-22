from piccolo.conf.apps import AppConfig

from .commands.new import new

APP_CONFIG = AppConfig(
    app_name="project", migrations_folder_path="", commands=[new]
)
