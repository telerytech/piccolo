from __future__ import annotations

import os
import shutil
import typing as t

import black  # type: ignore
import colorama  # type: ignore
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates/starlette/")
SERVERS = ["uvicorn", "Hypercorn"]
ROUTERS = ["starlette", "fastapi"]


def print_instruction(message: str):
    print(f"{colorama.Fore.CYAN}{message}{colorama.Fore.RESET}")


def get_options_string(options: t.List[str]):
    return ", ".join(
        [f"{name} [{index}]" for index, name in enumerate(options)]
    )


def get_routing_framework() -> str:
    print_instruction("Which routing framework?")
    router = input(f"{get_options_string(ROUTERS)}\n") or 0
    return ROUTERS[int(router)]


def get_server() -> str:
    print_instruction("Which server?")
    server = input(f"{get_options_string(SERVERS)}\n") or 0
    return SERVERS[int(server)]


def new(root: str = ".", name: str = "piccolo_project"):
    """
    Create a basic ASGI app, including Piccolo, routing, and an admin.

    :param root:
        Where to create the app e.g. /my/folder. By default it creates the
        app in the current directory.
    :param name:
        The name of the app to create - this will be used to prepopulate things
        like the database name.

    """
    tree = os.walk(TEMPLATE_DIR)

    template_context = {
        "router": get_routing_framework(),
        "server": get_server(),
        "project_identifier": name.replace(" ", "_").lower(),
    }

    for directory in tree:
        dir_path, sub_dir_names, file_names = directory  # type: ignore

        output_dir_path = os.path.join(root, dir_path.split(TEMPLATE_DIR)[-1])

        if not os.path.exists(output_dir_path):
            folder_name = output_dir_path.split("/")[-1]
            if folder_name.startswith(("_", ".")):
                continue
            os.mkdir(dir_path)

        for sub_dir_name in sub_dir_names:
            if sub_dir_name.startswith("_"):
                continue

            sub_dir_path = os.path.join(output_dir_path, sub_dir_name)
            if not os.path.exists(sub_dir_path):
                os.mkdir(sub_dir_path)

        for file_name in file_names:
            if file_name.startswith("_"):
                continue

            extension = file_name.rsplit(".")[0]
            if extension in ("pyc",):
                continue

            if file_name.endswith(".jinja"):
                output_file_name = file_name.replace(".jinja", "")
                template = Environment(
                    loader=FileSystemLoader(searchpath=dir_path)
                ).get_template(file_name)

                output_contents = template.render(**template_context)

                if output_file_name.endswith(".py"):
                    try:
                        output_contents = black.format_str(
                            output_contents,
                            mode=black.FileMode(line_length=80),
                        )
                    except Exception as exception:
                        print(f"Problem processing {output_file_name}")
                        raise exception

                with open(
                    os.path.join(output_dir_path, output_file_name), "w"
                ) as f:
                    f.write(output_contents)
            else:
                if file_name.endswith(".jinja_raw"):
                    output_file_name = file_name.replace(
                        ".jinja_raw", ".jinja"
                    )
                else:
                    output_file_name = file_name

                shutil.copy(
                    os.path.join(dir_path, file_name),
                    os.path.join(output_dir_path, output_file_name),
                )

    print(
        "Run `pip install -r requirements.txt` and `python main.py` to get "
        "started."
    )
