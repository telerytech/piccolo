from __future__ import annotations

import os
import sys

import black  # type: ignore
import jinja2

TEMPLATE_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates"
)

JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIRECTORY),
    trim_blocks=True,
    lstrip_blocks=True,
)


def new_piccolo_conf(engine_name: str, force: bool = False, root: str = "."):
    print("Creating new piccolo_conf file ...")

    file_path = os.path.join(root, "piccolo_conf.py")

    if os.path.exists(file_path) and not force:
        sys.exit("The file already exists - exiting.")

    with open(file_path, "w") as f:
        template = JINJA_ENV.get_template("piccolo_conf.py.jinja")
        file_contents = template.render(engine_name=engine_name)
        file_contents = black.format_str(
            file_contents, mode=black.FileMode(line_length=82)
        )

        f.write(file_contents)


def new(engine: str = "postgres", force: bool = False, root: str = "."):
    """
    Creates a new Piccolo project file (piccolo_conf.py).

    :param engine:
        Which database backend you plan on using - options are sqlite or
        postgres.
    :param force:
        If True, it will override the piccolo_conf.py file if it already
        exists.
    :param root:
        Where to create the app e.g. /my/folder. By default it creates the
        app in the current directory.

    """
    new_piccolo_conf(engine_name=engine, force=force, root=root)
