from piccolo.conf.apps import AppConfig

from .commands.backwards import backwards
from .commands.check import check
from .commands.clean import clean
from .commands.forwards import forwards
from .commands.new import new

APP_CONFIG = AppConfig(
    app_name="migrations",
    migrations_folder_path="",
    commands=[backwards, check, clean, forwards, new],
)
