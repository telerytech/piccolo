import sys

from piccolo.apps.user.commands.create import (get_confirmed_password,
                                               get_password, get_username)
from piccolo.apps.user.tables import BaseUser


def change_password():
    """
    Change a user's password.
    """
    username = get_username()
    password = get_password()
    confirmed_password = get_confirmed_password()

    if not password == confirmed_password:
        sys.exit("Passwords don't match!")

    BaseUser.update_password_sync(user=username, password=password)

    print(f"Updated password for {username}")
    print(
        "If using session auth, we recommend invalidating this user's session."
    )
