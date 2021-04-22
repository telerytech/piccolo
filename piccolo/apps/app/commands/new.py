from __future__ import annotations

import os
import sys
import typing as t

import black  # type: ignore
import jinja2

TEMPLATE_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates"
)

JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIRECTORY),
)


def new_app(app_name: str, root: str = "."):
    print(f"Creating {app_name} app ...")

    app_root = os.path.join(root, app_name)

    if os.path.exists(app_root):
        sys.exit("Folder already exists - exiting.")
    os.mkdir(app_root)

    with open(os.path.join(app_root, "__init__.py"), "w"):
        pass

    templates: t.Dict[str, t.Any] = {
        "piccolo_app.py": {"app_name": app_name},
        "tables.py": {},
    }

    for filename, context in templates.items():
        with open(os.path.join(app_root, filename), "w") as f:
            template = JINJA_ENV.get_template(filename + ".jinja")
            file_contents = template.render(**context)
            file_contents = black.format_str(
                file_contents, mode=black.FileMode(line_length=80)
            )
            f.write(file_contents)

    migrations_folder_path = os.path.join(app_root, "piccolo_migrations")
    os.mkdir(migrations_folder_path)

    with open(os.path.join(migrations_folder_path, "__init__.py"), "w"):
        pass


def new(app_name: str, root: str = "."):
    """
    Creates a new Piccolo app.

    :param app_name:
        The name of the new app.
    :param root:
        Where to create the app e.g. /my/folder. By default it creates the
        app in the current directory.

    """
    new_app(app_name=app_name, root=root)
