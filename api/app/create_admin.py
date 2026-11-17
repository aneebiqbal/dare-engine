"""Create the first administrator.

Usage: make create-admin   (runs `python -m app.create_admin` in the api container)

Prompts for an email and a password. The password is never taken as an argument,
never printed and never logged.
"""
from __future__ import annotations

import getpass
import re

from . import db

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main() -> None:
    from argon2 import PasswordHasher

    email = input("Admin email: ").strip().lower()
    if not EMAIL.match(email):
        raise SystemExit("a valid email is required")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE lower(email) = %s", (email,))
            row = cur.fetchone()
    if row:
        print(f"An account already exists for {email}.")
        make_admin = input("Make it an admin? [y/N] ").strip().lower() == "y"
        if not make_admin:
            return
        password = getpass.getpass("New password: ")
        if len(password) < 10:
            raise SystemExit("password must be at least 10 characters")
        confirm = getpass.getpass("Repeat password: ")
        if password != confirm:
            raise SystemExit("passwords do not match")
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET role = 'admin', password_hash = %s WHERE id = %s",
                    (PasswordHasher().hash(password), row[0]),
                )
        print(f"{email} is now an admin.")
        return

    password = getpass.getpass("Password: ")
    if len(password) < 10:
        raise SystemExit("password must be at least 10 characters")
    confirm = getpass.getpass("Repeat password: ")
    if password != confirm:
        raise SystemExit("passwords do not match")

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, display_name, password_hash, role) "
                "VALUES (%s, %s, %s, 'admin')",
                (email, email.split("@")[0], PasswordHasher().hash(password)),
            )
    print(f"Admin created for {email}.")


if __name__ == "__main__":
    main()
