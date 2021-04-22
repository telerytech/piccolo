from piccolo.apps.migrations.auto import MigrationManager

ID = "2020-06-11T21:38:55"


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="user")

    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="first_name",
        column_class_name="Varchar",
        params={
            "length": 255,
            "default": "",
            "null": True,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    manager.add_column(
        table_class_name="BaseUser",
        tablename="piccolo_user",
        column_name="last_name",
        column_class_name="Varchar",
        params={
            "length": 255,
            "default": "",
            "null": True,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    return manager
