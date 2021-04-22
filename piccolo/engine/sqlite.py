from __future__ import annotations

import contextvars
import datetime
import os
import sqlite3
import typing as t
import uuid
from dataclasses import dataclass
from decimal import Decimal

from aiosqlite import Connection, Cursor, connect

from piccolo.engine.base import Batch, Engine
from piccolo.engine.exceptions import TransactionError
from piccolo.query.base import Query
from piccolo.querystring import QueryString
from piccolo.utils.sync import run_sync

###############################################################################

# We need to register some adapters so sqlite returns types which are more
# consistent with the Postgres engine.


# In


def convert_numeric_in(value):
    """
    Convert any Decimal values into floats.
    """
    return float(value)


def convert_uuid_in(value) -> str:
    """
    Converts the UUID value being passed into sqlite.
    """
    return str(value)


def convert_time_in(value) -> str:
    """
    Converts the time value being passed into sqlite.
    """
    return value.isoformat()


def convert_date_in(value):
    """
    Converts the date value being passed into sqlite.
    """
    return value.isoformat()


def convert_datetime_in(value: datetime.datetime) -> str:
    """
    Converts the datetime into a string. If it's timezone aware, we want to
    convert it to UTC first. This is to replicate Postgres, which stores
    timezone aware datetimes in UTC.
    """
    if value.tzinfo is not None:
        value = value.astimezone(datetime.timezone.utc)
    return str(value)


def convert_timedelta_in(value):
    """
    Converts the timedelta value being passed into sqlite.
    """
    return value.total_seconds()


# Out


def convert_numeric_out(value: bytes) -> Decimal:
    """
    Convert float values into Decimals.
    """
    return Decimal(value.decode("ascii"))


def convert_int_out(value: bytes) -> int:
    """
    Make sure Integer values are actually of type int.
    """
    return int(float(value))


def convert_uuid_out(value: bytes) -> uuid.UUID:
    """
    If the value is a uuid, convert it to a UUID instance.
    """
    return uuid.UUID(value.decode("utf8"))


def convert_date_out(value: bytes) -> datetime.date:
    return datetime.date.fromisoformat(value.decode("utf8"))


def convert_time_out(value: bytes) -> datetime.time:
    """
    If the value is a time, convert it to a UUID instance.
    """
    return datetime.time.fromisoformat(value.decode("utf8"))


def convert_seconds_out(value: bytes) -> datetime.timedelta:
    """
    If the value is from a seconds column, convert it to a timedelta instance.
    """
    return datetime.timedelta(seconds=float(value.decode("utf8")))


def convert_boolean_out(value: bytes) -> bool:
    """
    If the value is from a boolean column, convert it to a bool value.
    """
    _value = value.decode("utf8")
    return _value == "1"


def convert_timestamptz_out(value: bytes) -> datetime.datetime:
    """
    If the value is from a timstamptz column, convert it to a datetime value,
    with a timezone of UTC.
    """
    return datetime.datetime.fromisoformat(value.decode("utf8"))


sqlite3.register_converter("Numeric", convert_numeric_out)
sqlite3.register_converter("Integer", convert_int_out)
sqlite3.register_converter("UUID", convert_uuid_out)
sqlite3.register_converter("Date", convert_date_out)
sqlite3.register_converter("Time", convert_time_out)
sqlite3.register_converter("Seconds", convert_seconds_out)
sqlite3.register_converter("Boolean", convert_boolean_out)
sqlite3.register_converter("Timestamptz", convert_timestamptz_out)

sqlite3.register_adapter(Decimal, convert_numeric_in)
sqlite3.register_adapter(uuid.UUID, convert_uuid_in)
sqlite3.register_adapter(datetime.time, convert_time_in)
sqlite3.register_adapter(datetime.date, convert_date_in)
sqlite3.register_adapter(datetime.datetime, convert_datetime_in)
sqlite3.register_adapter(datetime.timedelta, convert_timedelta_in)

###############################################################################


@dataclass
class AsyncBatch(Batch):

    connection: Connection
    query: Query
    batch_size: int

    # Set internally
    _cursor: t.Optional[Cursor] = None

    @property
    def cursor(self) -> Cursor:
        if not self._cursor:
            raise ValueError("_cursor not set")
        return self._cursor

    async def next(self) -> t.List[t.Dict]:
        data = await self.cursor.fetchmany(self.batch_size)
        return await self.query._process_results(data)

    def __aiter__(self):
        return self

    async def __anext__(self):
        response = await self.next()
        if response == []:
            raise StopAsyncIteration()
        return response

    async def __aenter__(self):
        querystring = self.query.querystrings[0]
        template, template_args = querystring.compile_string()

        self._cursor = await self.connection.execute(template, *template_args)
        return self

    async def __aexit__(self, exception_type, exception, traceback):
        await self._cursor.close()
        await self.connection.close()
        return exception is not None


###############################################################################


class Atomic:
    """
    Usage:

    transaction = engine.atomic()
    transaction.add(Foo.create_table())

    # Either:
    transaction.run_sync()
    await transaction.run()
    """

    __slots__ = ("engine", "queries")

    def __init__(self, engine: SQLiteEngine):
        self.engine = engine
        self.queries: t.List[Query] = []

    def add(self, *query: Query):
        self.queries += list(query)

    async def run(self):
        connection = await self.engine.get_connection()
        await connection.execute("BEGIN")

        try:
            for query in self.queries:
                for querystring in query.querystrings:
                    await connection.execute(
                        *querystring.compile_string(
                            engine_type=self.engine.engine_type
                        )
                    )
        except Exception as exception:
            await connection.execute("ROLLBACK")
            await connection.close()
            self.queries = []
            raise exception
        else:
            await connection.execute("COMMIT")
            await connection.close()
            self.queries = []

    def run_sync(self):
        return run_sync(self.run())


###############################################################################


class Transaction:
    """
    Used for wrapping queries in a transaction, using a context manager.
    Currently it's async only.

    Usage:

    async with engine.transaction():
        # Run some queries:
        await Band.select().run()

    """

    __slots__ = ("engine", "context", "connection")

    def __init__(self, engine: SQLiteEngine):
        self.engine = engine
        if self.engine.transaction_connection.get():
            raise TransactionError(
                "A transaction is already active - nested transactions aren't "
                "currently supported."
            )

    async def __aenter__(self):
        self.connection = await self.engine.get_connection()
        await self.connection.execute("BEGIN")
        self.context = self.engine.transaction_connection.set(self.connection)

    async def __aexit__(self, exception_type, exception, traceback):
        if exception:
            await self.connection.execute("ROLLBACK")
        else:
            await self.connection.execute("COMMIT")

        await self.connection.close()
        self.engine.transaction_connection.reset(self.context)

        return exception is None


###############################################################################


def dict_factory(cursor, row) -> t.Dict:
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SQLiteEngine(Engine):
    """
    Any connection kwargs are passed into the database adapter.

    See here for more info:
    https://docs.python.org/3/library/sqlite3.html#sqlite3.connect

    """

    __slots__ = ("connection_kwargs",)

    engine_type = "sqlite"
    min_version_number = 3.25

    def __init__(
        self,
        path: str = "piccolo.sqlite",
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,
        **connection_kwargs,
    ) -> None:
        connection_kwargs.update(
            {
                "database": path,
                "detect_types": detect_types,
                "isolation_level": isolation_level,
            }
        )
        self.connection_kwargs = connection_kwargs

        self.transaction_connection = contextvars.ContextVar(
            f"sqlite_transaction_connection_{path}", default=None
        )

        super().__init__()

    @property
    def path(self):
        return self.connection_kwargs["database"]

    @path.setter
    def path(self, value: str):
        self.connection_kwargs["database"] = value

    async def get_version(self) -> float:
        """
        Warn if the version of SQLite isn't supported.
        """
        major, minor, _ = sqlite3.sqlite_version_info
        return float(f"{major}.{minor}")

    async def prep_database(self):
        pass

    ###########################################################################

    def remove_db_file(self):
        """
        Use with caution - removes the sqlite file. Useful for testing
        purposes.
        """
        if os.path.exists(self.path):
            os.unlink(self.path)

    def create_db(self, migrate=False):
        """
        Create the database file, with the option to run migrations. Useful
        for testing purposes.
        """
        if not os.path.exists(self.path):
            with open(self.path, "w"):
                pass
        else:
            raise Exception(f"Database at {self.path} already exists")
        if migrate:
            # Commented out for now, as migrations for SQLite aren't as
            # well supported as Postgres.
            # from piccolo.commands.migration.forwards import (
            #     ForwardsMigrationManager,
            # )

            # ForwardsMigrationManager().run()
            pass

    ###########################################################################

    async def batch(self, query: Query, batch_size: int = 100) -> AsyncBatch:
        connection = await self.get_connection()
        return AsyncBatch(
            connection=connection, query=query, batch_size=batch_size
        )

    ###########################################################################

    async def get_connection(self) -> Connection:
        connection = await connect(**self.connection_kwargs)
        connection.row_factory = dict_factory  # type: ignore
        await connection.execute("PRAGMA foreign_keys = 1")
        return connection

    ###########################################################################

    async def _run_in_new_connection(
        self, query: str, args: t.List[t.Any] = [], query_type: str = "generic"
    ):
        async with connect(**self.connection_kwargs) as connection:
            await connection.execute("PRAGMA foreign_keys = 1")

            connection.row_factory = dict_factory  # type: ignore
            async with connection.execute(query, args) as cursor:
                await connection.commit()
                response = await cursor.fetchall()

                if query_type == "insert":
                    return [{"id": cursor.lastrowid}]
                else:
                    return response

    async def _run_in_existing_connection(
        self,
        connection,
        query: str,
        args: t.List[t.Any] = [],
        query_type: str = "generic",
    ):
        """
        This is used when a transaction is currently active.
        """
        await connection.execute("PRAGMA foreign_keys = 1")

        connection.row_factory = dict_factory
        async with connection.execute(query, args) as cursor:
            response = await cursor.fetchall()

            if query_type == "insert":
                return [{"id": cursor.lastrowid}]
            else:
                return response

    async def run_querystring(
        self, querystring: QueryString, in_pool: bool = False
    ):
        """
        Connection pools aren't currently supported - the argument is there
        for consistency with other engines.
        """
        query, query_args = querystring.compile_string(
            engine_type=self.engine_type
        )

        # If running inside a transaction:
        connection = self.transaction_connection.get()
        if connection:
            return await self._run_in_existing_connection(
                connection=connection,
                query=query,
                args=query_args,
                query_type=querystring.query_type,
            )

        return await self._run_in_new_connection(
            query=query, args=query_args, query_type=querystring.query_type
        )

    def atomic(self) -> Atomic:
        return Atomic(engine=self)

    def transaction(self) -> Transaction:
        return Transaction(engine=self)
