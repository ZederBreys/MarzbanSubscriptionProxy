"""
CLI entry point for administrative operations.

Usage:
    python -m app.cli create-admin
"""

import getpass
import sqlite3
import sys


def _create_admin() -> None:
    from app.database.connection import init_db
    from app.database.connection import get_connection
    from app.core.security import hash_password

    init_db()

    print("Create Admin User")
    print("-" * 40)

    login = input("Login: ").strip()
    if not login:
        print("Login cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    password_hash = hash_password(password)

    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO admin_users (login, password_hash) VALUES (?, ?)",
                (login, password_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            print(f"Admin '{login}' already exists.")
            sys.exit(1)

    print(f"Admin '{login}' created successfully.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli <command>")
        print("Commands:")
        print("  create-admin  Create initial administrator account")
        sys.exit(1)

    command = sys.argv[1]
    if command == "create-admin":
        _create_admin()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
