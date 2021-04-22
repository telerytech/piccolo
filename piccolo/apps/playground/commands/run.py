"""
Populates a database with an example schema and data, and launches a shell
for interacting with the data using Piccolo.
"""
import datetime
import sys
import uuid
from decimal import Decimal

from piccolo.columns import (UUID, Boolean, ForeignKey, Integer, Interval,
                             Numeric, Timestamp, Varchar)
from piccolo.engine import PostgresEngine, SQLiteEngine
from piccolo.engine.base import Engine
from piccolo.table import Table


class Manager(Table):
    name = Varchar(length=50)


class Band(Table):
    name = Varchar(length=50)
    manager = ForeignKey(references=Manager, null=True)
    popularity = Integer()


class Venue(Table):
    name = Varchar(length=100)
    capacity = Integer(default=0)


class Concert(Table):
    band_1 = ForeignKey(Band)
    band_2 = ForeignKey(Band)
    venue = ForeignKey(Venue)
    starts = Timestamp()
    duration = Interval()


class Ticket(Table):
    concert = ForeignKey(Concert)
    price = Numeric(digits=(5, 2))


class DiscountCode(Table):
    code = UUID()
    active = Boolean(default=True, null=True)


TABLES = (Manager, Band, Venue, Concert, Ticket, DiscountCode)


def populate():
    """
    Drop then recreate the tables, and populate with data.
    """
    for _table in reversed(TABLES):
        try:
            if _table.table_exists().run_sync():
                _table.alter().drop_table().run_sync()
        except Exception as e:
            print(e)

    for _table in TABLES:
        try:
            _table.create_table().run_sync()
        except Exception as e:
            print(e)

    guido = Manager(name="Guido")
    guido.save().run_sync()

    pythonistas = Band(name="Pythonistas", manager=guido.id, popularity=1000)
    pythonistas.save().run_sync()

    graydon = Manager(name="Graydon")
    graydon.save().run_sync()

    rustaceans = Band(name="Rustaceans", manager=graydon.id, popularity=500)
    rustaceans.save().run_sync()

    venue = Venue(name="Amazing Venue", capacity=5000)
    venue.save().run_sync()

    concert = Concert(
        band_1=pythonistas.id,
        band_2=rustaceans.id,
        venue=venue.id,
        starts=datetime.datetime.now() + datetime.timedelta(days=7),
        duration=datetime.timedelta(hours=2),
    )
    concert.save().run_sync()

    ticket = Ticket(concert=concert.id, price=Decimal("50.0"))
    ticket.save().run_sync()

    discount_code = DiscountCode(code=uuid.uuid4())
    discount_code.save().run_sync()


def run(
    engine: str = "sqlite",
    user: str = "piccolo",
    password: str = "piccolo",
    database: str = "piccolo_playground",
    host: str = "localhost",
    port: int = 5432,
):
    """
    Creates a test database to play with.

    :param engine:
        Which database engine to use - options are sqlite or postgres
    :param user:
        Postgres user
    :param password:
        Postgres password
    :param database:
        Postgres database
    :param host:
        Postgres host
    :param port:
        Postgres port
    """
    try:
        import IPython  # type: ignore
    except ImportError:
        sys.exit(
            "Install iPython using `pip install ipython` to use this feature."
        )

    if engine.upper() == "POSTGRES":
        db: Engine = PostgresEngine(
            {
                "host": host,
                "database": database,
                "user": user,
                "password": password,
                "port": port,
            }
        )
        for _table in TABLES:
            _table._meta._db = db
    else:
        db = SQLiteEngine()
        for _table in TABLES:
            _table._meta._db = db

    print("Tables:\n")

    for _table in TABLES:
        print(_table._table_str(abbreviated=True))
        print("\n")

    print("Try it as a query builder:")
    print("Band.select().run_sync()")
    print("Band.select(Band.name).run_sync()")
    print("Band.select(Band.name, Band.manager.name).run_sync()")
    print("\n")

    print("Try it as an ORM:")
    print(
        "b = Band.objects().where(Band.name == 'Pythonistas').first()."
        "run_sync()"
    )
    print("b.popularity = 10000")
    print("b.save().run_sync()")
    print("\n")

    populate()

    from IPython.core.interactiveshell import _asyncio_runner  # type: ignore

    IPython.embed(using=_asyncio_runner)
