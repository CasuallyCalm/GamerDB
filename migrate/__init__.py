"""
For migrating from the old GamerDB database schema to the new one
"""
import json
import sqlite3
from pathlib import Path
from gamerdb.sql import CreateTable, Mutation, Query


class Migrator:
    def __init__(self, old_db: Path) -> None:
        self.old_db = sqlite3.connect(old_db)
        self.old_db.row_factory = sqlite3.Row
        self.old_platforms = json.load(open(old_db.parent.joinpath("platforms.json")))
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
        data = [
            (platform, settings.get("emoji"))
            for platform, settings in self.old_platforms.items()
        ]
        self.new_db.executemany(Mutation.add_platform, data)
        self.new_db.commit()

    def __migrate_users(self):
        cur = self.old_db.execute("SELECT * FROM database")
        columns = [description[0] for description in cur.description]
        users = cur.fetchall()
        profiles = []
        for col in columns[2:]:
            for user in users:
                if user[col]:
                    platform = self.new_db.execute(
                        "SELECT id FROM platforms WHERE name=?", (col,)
                    ).fetchone()
                    profiles.append((user["player"], user[col], platform[0]))

        self.new_db.executemany(Mutation.register_player, profiles)
        self.new_db.commit()

    def migrate(self):
        # print("Migrating guild prefixes")
        # self.__migrate_guilds()
        # print("Migrating platforms")
        # self.__migrate_platforms()
        print("Migrating user profiles")
        self.__migrate_users()


def main():
    old_db_name = input("Name of database to migrate[gdb.db]:") or "gdb.db"
    old_db_path = Path(f"./migrate/old_db/{old_db_name}")
    if old_db_path.is_file():
        Migrator(old_db_path).migrate()
    else:
        print('Invalid database name, file must be in the "migrate/old_db" folder!')


if __name__ == "__main__":
    main()
