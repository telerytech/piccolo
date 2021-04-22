import typing as t
from dataclasses import dataclass

from piccolo.columns.base import Column


@dataclass
class RenameTable:
    old_class_name: str
    old_tablename: str
    new_class_name: str
    new_tablename: str


@dataclass
class RenameColumn:
    table_class_name: str
    tablename: str
    old_column_name: str
    new_column_name: str


@dataclass
class AlterColumn:
    table_class_name: str
    column_name: str
    tablename: str
    params: t.Dict[str, t.Any]
    old_params: t.Dict[str, t.Any]
    column_class: t.Optional[t.Type[Column]] = None
    old_column_class: t.Optional[t.Type[Column]] = None


@dataclass
class DropColumn:
    table_class_name: str
    column_name: str
    tablename: str


@dataclass
class AddColumn:
    table_class_name: str
    column_name: str
    column_class_name: str
    column_class: t.Type[Column]
    params: t.Dict[str, t.Any]
