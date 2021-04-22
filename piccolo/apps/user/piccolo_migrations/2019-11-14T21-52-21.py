from piccolo.apps.migrations.auto import MigrationManager

ID = "2019-11-14T21:52:21"


async def forwards():
    manager = MigrationManager(migration_id=ID)
    manager.add_table("BaseUser", tablename="piccolo_user")
    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="username",
        column_class_name="Varchar",
        params={
            "length": 100,
            "default": "",
            "null": False,
            "primary": False,
            "key": False,
            "unique": True,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="password",
        column_class_name="Secret",
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="email",
        column_class_name="Varchar",
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary": False,
            "key": False,
            "unique": True,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="active",
        column_class_name="Boolean",
        params={
            "default": False,
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="admin",
        column_class_name="Boolean",
        params={
            "default": False,
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    return manager
