from piccolo.conf.apps import AppConfig

from .commands.new import new
from .commands.show_all import show_all

APP_CONFIG = AppConfig(
    app_name="app", migrations_folder_path="", commands=[new, show_all]
)
