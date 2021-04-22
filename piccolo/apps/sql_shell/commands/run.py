import os
import signal
import subprocess
import typing as t

from piccolo.engine.finder import engine_finder
from piccolo.engine.postgres import PostgresEngine
from piccolo.engine.sqlite import SQLiteEngine

if t.TYPE_CHECKING:  # pragma: no cover
    from piccolo.engine.base import Engine


def run():
    """
    Launch the SQL shell for the configured engine. For Postgres
    this will be psql, and for SQLite it will be sqlite3.
    """
    engine: t.Optional[Engine] = engine_finder()

    if engine is None:
        raise ValueError(
            "Unable to find the engine - make sure piccolo_conf is on the "
            "path."
        )

    # Heavily inspired by Django's dbshell command
    if isinstance(engine, PostgresEngine):
        engine: PostgresEngine = engine

        args = ["psql"]

        host = engine.config.get("host")
        port = engine.config.get("port")
        user = engine.config.get("user")
        password = engine.config.get("password")
        database = engine.config.get("database")

        if user:
            args += ["-U", user]
        if host:
            args += ["-h", host]
        if port:
            args += ["-p", str(port)]
        args += [database]

        sigint_handler = signal.getsignal(signal.SIGINT)
        subprocess_env = os.environ.copy()
        if password:
            subprocess_env["PGPASSWORD"] = str(password)
        try:
            # Allow SIGINT to pass to psql to abort queries.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("Enter \\q to exit")
            subprocess.run(args, check=True, env=subprocess_env)
        finally:
            # Restore the original SIGINT handler.
            signal.signal(signal.SIGINT, sigint_handler)

    elif isinstance(engine, SQLiteEngine):
        engine: SQLiteEngine = engine
        print("Enter .quit to exit")
        subprocess.run(
            ["sqlite3", engine.connection_kwargs.get("database")], check=True
        )
