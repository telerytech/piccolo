from __future__ import annotations

import inspect
import itertools
import typing as t
from dataclasses import dataclass, field

from piccolo.columns import Column, Selectable
from piccolo.columns.column_types import ForeignKey, PrimaryKey
from piccolo.columns.defaults.base import Default
from piccolo.columns.indexes import IndexMethod
from piccolo.columns.readable import Readable
from piccolo.columns.reference import (LAZY_COLUMN_REFERENCES,
                                       LazyTableReference)
from piccolo.custom_types import Combinable
from piccolo.engine import Engine, engine_finder
from piccolo.query import (Alter, Count, Create, Delete, DropIndex, Exists,
                           Insert, Objects, Raw, Select, TableExists, Update)
from piccolo.query.methods.create_index import CreateIndex
from piccolo.query.methods.indexes import Indexes
from piccolo.querystring import QueryString, Unquoted
from piccolo.utils import _camel_to_snake

PROTECTED_TABLENAMES = ("user",)


@dataclass
class TableMeta:
    """
    This is used to store info about the table.
    """

    tablename: str = ""
    columns: t.List[Column] = field(default_factory=list)
    default_columns: t.List[Column] = field(default_factory=list)
    non_default_columns: t.List[Column] = field(default_factory=list)
    foreign_key_columns: t.List[ForeignKey] = field(default_factory=list)
    tags: t.List[str] = field(default_factory=list)
    help_text: t.Optional[str] = None
    _db: t.Optional[Engine] = None
    pre_insert: t.List[t.Callable] = field(default_factory=list)
    post_insert: t.List[t.Callable] = field(default_factory=list)
    pre_update: t.List[t.Callable] = field(default_factory=list)
    post_update: t.List[t.Callable] = field(default_factory=list)
    pre_delete: t.List[t.Callable] = field(default_factory=list)
    post_delete: t.List[t.Callable] = field(default_factory=list)


    # Records reverse foreign key relationships - i.e. when the current table
    # is the target of a foreign key. Used by external libraries such as
    # Piccolo API.
    _foreign_key_references: t.List[ForeignKey] = field(default_factory=list)

    @property
    def foreign_key_references(self) -> t.List[ForeignKey]:
        foreign_keys: t.List[ForeignKey] = []
        for reference in self._foreign_key_references:
            foreign_keys.append(reference)

        lazy_column_references = LAZY_COLUMN_REFERENCES.for_tablename(
            tablename=self.tablename
        )
        foreign_keys.extend(lazy_column_references)

        return foreign_keys

    @property
    def db(self) -> Engine:
        if not self._db:
            db = engine_finder()
            if not db:
                raise Exception("Unable to find the engine")
            self._db = db

        return self._db

    def get_column_by_name(self, name: str) -> Column:
        """
        Returns a column which matches the given name. It will try and follow
        foreign keys too, for example if the name is 'foo.bar', where foo is
        a foreign key, and bar is a column on the referenced table.
        """
        components = name.split(".")
        column_name = components[0]
        column = [i for i in self.columns if i._meta.name == column_name]
        if len(column) != 1:
            raise ValueError(f"No matching column found with name == {name}")
        column_object = column[0]

        if len(components) > 1:
            for reference_name in components[1:]:
                try:
                    column_object = getattr(column_object, reference_name)
                except AttributeError:
                    raise ValueError(
                        f"Unable to find column - {reference_name}"
                    )

        return column_object


class TableMetaclass(type):
    def __str__(cls):
        return cls._table_str()


class Table(metaclass=TableMetaclass):

    # These are just placeholder values, so type inference isn't confused - the
    # actual values are set in __init_subclass__.
    _meta = TableMeta()
    id = PrimaryKey()

    def __init_subclass__(
        cls,
        tablename: t.Optional[str] = None,
        db: t.Optional[Engine] = None,
        tags: t.List[str] = [],
        help_text: t.Optional[str] = None,
        pre_insert: t.List[t.Callable] = [],
        post_insert: t.List[t.Callable] = [],
        pre_update: t.List[t.Callable] = [],
        post_update: t.List[t.Callable] = [],
        pre_delete: t.List[t.Callable] = [],
        post_delete: t.List[t.Callable] = []
    ):
        """
        Automatically populate the _meta, which includes the tablename, and
        columns.

        :param tablename:
            Specify a custom tablename. By default the classname is converted
            to snakecase.

        :param db:
            Manually specify an engine to use for connecting to the database.
            Useful when writing simple scripts. If not set, the engine is
            imported from piccolo_conf.py using ``engine_finder``.

        :param tags:
            Used for filtering, for example by ``table_finder``.

        :param help_text:
            A user friendly description of what the table is used for. It isn't
            used in the database, but will be used by tools such a Piccolo
            Admin for tooltips.
       
        :param pre_insert:
            Used for defining list of functions to be run before insert

        :param post_insert:
            Used for defining list of functions to be run after insert

        :param pre_update:
            used for defining list of functions to be run before update

        :param post_update:
            used for defining list of functions to be run after update
        
        :param pre_delete:
            used for defining list of functions to be run before delete

        :param post_delete:
            used for defining list of functions to be run after delete

        """
        tablename = tablename if tablename else _camel_to_snake(cls.__name__)

        if tablename in PROTECTED_TABLENAMES:
            raise ValueError(
                f"{tablename} is a protected name, please give your table a "
                "different name."
            )

        columns: t.List[Column] = []
        default_columns: t.List[Column] = []
        non_default_columns: t.List[Column] = []
        foreign_key_columns: t.List[ForeignKey] = []

        cls.id = PrimaryKey()

        attribute_names = itertools.chain(
            *[i.__dict__.keys() for i in reversed(cls.__mro__)]
        )
        unique_attribute_names = list(dict.fromkeys(attribute_names))

        for attribute_name in unique_attribute_names:
            if attribute_name.startswith("_"):
                continue

            attribute = getattr(cls, attribute_name)
            if isinstance(attribute, Column):
                column = attribute

                if isinstance(column, PrimaryKey):
                    # We want it at the start.
                    columns = [column] + columns  # type: ignore
                    default_columns.append(column)
                else:
                    columns.append(column)
                    non_default_columns.append(column)

                column._meta._name = attribute_name
                column._meta._table = cls

            if isinstance(column, ForeignKey):
                foreign_key_columns.append(column)

        cls._meta = TableMeta(
            tablename=tablename,
            columns=columns,
            default_columns=default_columns,
            non_default_columns=non_default_columns,
            foreign_key_columns=foreign_key_columns,
            tags=tags,
            help_text=help_text,
            _db=db,
            pre_insert=pre_insert,
            post_insert=post_insert,
            pre_update=pre_update,
            post_update=post_update,
            pre_delete=pre_delete,
            post_delete=post_delete
        )

        for foreign_key_column in foreign_key_columns:
            params = foreign_key_column._meta.params
            references = params["references"]

            if isinstance(references, str):
                if references == "self":
                    references = cls
                else:
                    if "." in references:
                        # Don't allow relative modules - this may change in
                        # the future.
                        if references.startswith("."):
                            raise ValueError("Relative imports aren't allowed")

                        module_path, table_class_name = references.rsplit(
                            ".", maxsplit=1
                        )
                    else:
                        table_class_name = references
                        module_path = cls.__module__

                    references = LazyTableReference(
                        table_class_name=table_class_name,
                        module_path=module_path,
                    )

            is_lazy = isinstance(references, LazyTableReference)
            is_table_class = inspect.isclass(references) and issubclass(
                references, Table
            )

            if is_lazy or is_table_class:
                foreign_key_column._foreign_key_meta.references = references
            else:
                raise ValueError(
                    "Error - ``references`` must be a ``Table`` subclass, or "
                    "a ``LazyTableReference`` instance."
                )

            # Record the reverse relationship on the target table.
            if is_table_class:
                references._meta._foreign_key_references.append(
                    foreign_key_column
                )
            elif is_lazy:
                LAZY_COLUMN_REFERENCES.foreign_key_columns.append(
                    foreign_key_column
                )

            # Allow columns on the referenced table to be accessed via
            # auto completion.
            if is_table_class:
                foreign_key_column.set_proxy_columns()

    def __init__(self, ignore_missing: bool = False, **kwargs):
        """
        Assigns any default column values to the class.
        """
        for column in self._meta.columns:
            value = kwargs.pop(column._meta.name, ...)
            if value is ...:
                value = column.get_default_value()

                if isinstance(value, Default):
                    value = value.python()

                if (
                    (value is None)
                    and (not column._meta.null)
                    and not ignore_missing
                ):
                    raise ValueError(f"{column._meta.name} wasn't provided")

            self[column._meta.name] = value

        unrecognized = kwargs.keys()
        if unrecognized:
            unrecognised_list = [i for i in unrecognized]
            raise ValueError(f"Unrecognized columns - {unrecognised_list}")

    ###########################################################################

    def get(self, *where: Combinable, **kwargs):
        """
         A proxy to an insert or update query.
        """
        return self.objects().where(*where, **kwargs).first()

    def save(self) -> t.Union[Insert, Update]:
        """
        A proxy to an insert or update query.
        """
        if not hasattr(self, "id"):
            raise ValueError("No id value found")

        cls = self.__class__

        if isinstance(self.id, int):
            # pre-existing row
            kwargs: t.Dict[Column, t.Any] = {
                i: getattr(self, i._meta.name, None)
                for i in cls._meta.columns
                if i._meta.name != "id"
            }
            return cls.update().values(kwargs).where(cls.id == self.id)
        else:
            return cls.insert().add(self)

    def remove(self) -> Delete:
        """
        A proxy to a delete query.
        """
        _id = self.id

        if not isinstance(_id, int):
            raise ValueError("Can only delete pre-existing rows with an id.")

        self.id = None  # type: ignore

        return self.__class__.delete().where(self.__class__.id == _id)

    def get_related(self, foreign_key: t.Union[ForeignKey, str]) -> Objects:
        """
        Used to fetch a Table instance, for the target of a foreign key.

        band = await Band.objects().first().run()
        manager = await band.get_related(Band.manager).run()
        >>> print(manager.name)
        'Guido'

        It can only follow foreign keys one level currently.
        i.e. Band.manager, but not Band.manager.x.y.z

        """
        if isinstance(foreign_key, str):
            column = self._meta.get_column_by_name(foreign_key)
            if isinstance(column, ForeignKey):
                foreign_key = column

        if not isinstance(foreign_key, ForeignKey):
            raise ValueError(
                "foreign_key isn't a ForeignKey instance,  or the name of a "
                "ForeignKey column."
            )

        column_name = foreign_key._meta.name

        references: t.Type[
            Table
        ] = foreign_key._foreign_key_meta.resolved_references

        return (
            references.objects()
            .where(
                references._meta.get_column_by_name("id")
                == getattr(self, column_name)
            )
            .first()
        )

    def __setitem__(self, key: str, value: t.Any):
        setattr(self, key, value)

    def __getitem__(self, key: str):
        return getattr(self, key)

    ###########################################################################

    @classmethod
    def _get_related_readable(cls, column: ForeignKey) -> Readable:
        """
        Used for getting a readable from a foreign key.
        """
        readable: Readable = (
            column._foreign_key_meta.resolved_references.get_readable()
        )

        columns = [getattr(column, i._meta.name) for i in readable.columns]

        output_name = f"{column._meta.name}_readable"

        new_readable = Readable(
            template=readable.template,
            columns=columns,
            output_name=output_name,
        )
        return new_readable

    @classmethod
    def get_readable(cls) -> Readable:
        """
        Creates a readable representation of the row.
        """
        return Readable(template="%s", columns=[cls.id])

    ###########################################################################

    @property
    def querystring(self) -> QueryString:
        """
        Used when inserting rows.
        """
        args_dict = {
            col._meta.name: self[col._meta.name] for col in self._meta.columns
        }

        def is_unquoted(arg):
            return type(arg) == Unquoted

        # Strip out any args which are unquoted.
        # TODO Not the cleanest place to have it (would rather have it handled
        # in the QueryString bundle logic) - might need refactoring.
        filtered_args = [i for i in args_dict.values() if not is_unquoted(i)]

        # If unquoted, dump it straight into the query.
        query = ",".join(
            [
                args_dict[column._meta.name].value
                if is_unquoted(args_dict[column._meta.name])
                else "{}"
                for column in self._meta.columns
            ]
        )
        return QueryString(f"({query})", *filtered_args)

    def __str__(self) -> str:
        return self.querystring.__str__()

    def __repr__(self) -> str:
        _id = self.id if isinstance(self.id, int) else None
        return f"<{self.__class__.__name__}: {_id}>"

    ###########################################################################
    # Classmethods

    @classmethod
    def ref(cls, column_name: str) -> Column:
        """
        Used to get a copy of a column from a table referenced by a
        ``ForeignKey`` column. It's unlikely an end user of this library will
        ever need to do this, but other libraries built on top of Piccolo may
        need this functionality.

        Example: Band.ref('manager.name')

        """
        local_column_name, reference_column_name = column_name.split(".")

        local_column = cls._meta.get_column_by_name(local_column_name)

        if not isinstance(local_column, ForeignKey):
            raise ValueError(f"{local_column_name} isn't a ForeignKey")

        referenced_table = local_column._foreign_key_meta.resolved_references
        reference_column = referenced_table._meta.get_column_by_name(
            reference_column_name
        )

        _reference_column = reference_column.copy()
        _reference_column._meta.name = (
            f"{local_column_name}.{reference_column_name}"
        )
        return _reference_column

    @classmethod
    def insert(cls, *rows: "Table") -> Insert:
        """
        await Band.insert(
            Band(name="Pythonistas", popularity=500, manager=1)
        ).run()
        """
        query = Insert(table=cls)
        if rows:
            query.add(*rows)
        return query

    @classmethod
    def raw(cls, sql: str, *args: t.Any) -> Raw:
        """
        Execute raw SQL queries on the underlying engine - use with caution!

        await Band.raw('select * from band').run()

        Or passing in parameters:

        await Band.raw("select * from band where name = {}", 'Pythonistas')
        """
        return Raw(table=cls, querystring=QueryString(sql, *args))

    @classmethod
    def _process_column_args(
        cls, *columns: t.Union[Selectable, str]
    ) -> t.Sequence[Selectable]:
        """
        Users can specify some column arguments as either Column instances, or
        as strings representing the column name, for convenience.
        Convert any string arguments to column instances.
        """
        return [
            cls._meta.get_column_by_name(column)
            if (isinstance(column, str))
            else column
            for column in columns
        ]

    @classmethod
    def select(
        cls, *columns: t.Union[Selectable, str], exclude_secrets=False
    ) -> Select:
        """
        Get data in the form of a list of dictionaries, with each dictionary
        representing a row.

        These are all equivalent:

        await Band.select().columns(Band.name).run()
        await Band.select(Band.name).run()
        await Band.select('name').run()

        :param exclude_secrets: If True, any password fields are omitted from
        the response. Even though passwords are hashed, you still don't want
        them being passed over the network if avoidable.
        """
        _columns = cls._process_column_args(*columns)
        return Select(
            table=cls, columns_list=_columns, exclude_secrets=exclude_secrets
        )

    @classmethod
    def delete(cls, force=False) -> Delete:
        """
        Delete rows from the table.

        await Band.delete().where(Band.name == 'Pythonistas').run()

        Unless 'force' is set to True, deletions aren't allowed without a
        'where' clause, to prevent accidental mass deletions.
        """
        return Delete(table=cls, force=force)

    @classmethod
    def create_table(
        cls, if_not_exists=False, only_default_columns=False
    ) -> Create:
        """
        Create table, along with all columns.

        await Band.create_table().run()
        """
        return Create(
            table=cls,
            if_not_exists=if_not_exists,
            only_default_columns=only_default_columns,
        )

    @classmethod
    def alter(cls) -> Alter:
        """
        Used to modify existing tables and columns.

        await Band.alter().rename_column(Band.popularity, 'rating').run()
        """
        return Alter(table=cls)

    @classmethod
    def objects(cls) -> Objects:
        """
        Returns a list of table instances (each representing a row), which you
        can modify and then call 'save' on, or can delete by calling 'remove'.

        pythonistas = await Band.objects().where(
            Band.name == 'Pythonistas'
        ).first().run()

        pythonistas.name = 'Pythonistas Reborn'

        await pythonistas.save().run()

        # Or to remove it from the database:
        await pythonistas.remove()
        """
        return Objects(table=cls)

    @classmethod
    def count(cls) -> Count:
        """
        Count the number of matching rows.

        await Band.count().where(Band.popularity > 1000).run()
        """
        return Count(table=cls)

    @classmethod
    def exists(cls) -> Exists:
        """
        Use it to check if a row exists, not if the table exists.

        await Band.exists().where(Band.name == 'Pythonistas').run()
        """
        return Exists(table=cls)

    @classmethod
    def table_exists(cls) -> TableExists:
        """
        Check if the table exists in the database.

        await Band.table_exists().run()
        """
        return TableExists(table=cls)

    @classmethod
    def update(cls, values: t.Dict[Column, t.Any] = {}) -> Update:
        """
        Update rows.

        await Band.update().values(
            {Band.name: "Spamalot"}
        ).where(
            Band.name=="Pythonistas"
        ).run()
        """
        return Update(table=cls).values(values)

    @classmethod
    def indexes(cls) -> Indexes:
        """
        Returns a list of the indexes for this tables.

        await Band.indexes().run()
        """
        return Indexes(table=cls)

    @classmethod
    def create_index(
        cls,
        columns: t.List[t.Union[Column, str]],
        method: IndexMethod = IndexMethod.btree,
        if_not_exists: bool = False,
    ) -> CreateIndex:
        """
        Create a table index. If multiple columns are specified, this refers
        to a multicolumn index, rather than multiple single column indexes.

        await Band.create_index([Band.name]).run()
        """
        return CreateIndex(
            table=cls,
            columns=columns,
            method=method,
            if_not_exists=if_not_exists,
        )

    @classmethod
    def drop_index(
        cls, columns: t.List[t.Union[Column, str]], if_exists: bool = True
    ) -> DropIndex:
        """
        Drop a table index. If multiple columns are specified, this refers
        to a multicolumn index, rather than multiple single column indexes.

        await Band.drop_index([Band.name]).run()
        """
        return DropIndex(table=cls, columns=columns, if_exists=if_exists)

    ###########################################################################

    @classmethod
    def _get_index_name(cls, column_names: t.List[str]) -> str:
        """
        Generates an index name from the table name and column names.
        """
        return "_".join([cls._meta.tablename] + column_names)

    ###########################################################################

    @classmethod
    def _table_str(cls, abbreviated=False):
        """
        Returns a basic string representation of the table and its columns.
        Used by the playground.

        :param abbreviated:
            If True, a very high level representation is printed out.

        """
        spacer = "\n    "
        columns = []
        for col in cls._meta.columns:
            params: t.List[str] = []
            for key, value in col._meta.params.items():
                _value: str = ""
                if inspect.isclass(value):
                    _value = value.__name__
                    params.append(f"{key}={_value}")
                else:
                    _value = repr(value)
                    if not abbreviated:
                        params.append(f"{key}={_value}")
            params_string = ", ".join(params)
            columns.append(
                f"{col._meta.name} = {col.__class__.__name__}({params_string})"
            )
        columns_string = spacer.join(columns)
        tablename = repr(cls._meta.tablename)

        parent_class_name = cls.mro()[1].__name__

        class_args = (
            parent_class_name
            if abbreviated
            else f"{parent_class_name}, tablename={tablename}"
        )

        return (
            f"class {cls.__name__}({class_args}):\n" f"    {columns_string}\n"
        )
