"""
For migrating from the old GamerDB database schema to the new one
"""

import sqlite3
from pathlib import Path


def main():
    old_db_name = input("Name of database to migrate[gdb.db]:") or "gdb.db"
    old_db_path = Path(f"./migrate/old_db/{old_db_name}")
    if old_db_path.is_file():
        old_db = sqlite3.connect(old_db_path)

    else:
        print('Invalid database name, file must be in the "migrate/old_db" folder!')
