"""
For migrating from the old GamerDB database schema to the new one
"""

import sqlite3
from pathlib import Path
from gamerdb.sql import CreateTable, Mutation


class Migrator:
    def __init__(self, old_db: sqlite3.Connection) -> None:
        self.old_db = old_db
        self.new_db = sqlite3.connect("gamerdb.db")
        self.__create_new_tables()

    def __create_new_tables(self):
        self.new_db.execute(CreateTable.guilds)
        self.new_db.execute(CreateTable.platforms)
        self.new_db.execute(CreateTable.players)

    def __migrate_guilds(self):
        old_guilds = self.old_db.execute("SELECT guild, prefix FROM guild")
        self.new_db.executemany(Mutation.register_prefix, old_guilds.fetchall())
        self.new_db.commit()

    def __migrate_platforms(self):
        old_platforms = self.old_db.execute("SELECT * from database")
        names = [description[0] for description in old_platforms.description[2:]]

    def __migrate_users(self):
        pass

    def migrate(self):
        print("Migrating guilds")
        # self.__migrate_guilds()
        print("Migrating platforms")
        self.__migrate_platforms()
        self.__migrate_users()


def main():
    old_db_name = input("Name of database to migrate[gdb.db]:") or "gdb.db"
    old_db_path = Path(f"./migrate/old_db/{old_db_name}")
    if old_db_path.is_file():
        old_db = sqlite3.connect(old_db_path)
        Migrator(old_db).migrate()
    else:
        print('Invalid database name, file must be in the "migrate/old_db" folder!')


if __name__ == "__main__":
    main()