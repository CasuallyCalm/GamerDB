class CreateTable:

    players = """
        CREATE TABLE IF NOT EXISTS players (
          id INTEGER PRIMARY KEY,
          member_id INTEGER NOT NULL,
          gamertag TEXT NOT NULL,
          platform_id INTEGER,
          UNIQUE(member_id, platform_id),
          FOREIGN KEY (platform_id)
          REFERENCES platforms (id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        );
        """

    platforms = """
        CREATE TABLE IF NOT EXISTS platforms (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          emoji_id INTEGER NOT NULL UNIQUE
        );
        """


class Query:

    platforms = """
        SELECT * FROM platforms
        ORDER BY platforms.name
    """

    profile = """
        SELECT players.gamertag, platforms.name, platforms.emoji_id
        FROM players
        JOIN platforms
        ON players.platform_id = platforms.id
        AND players.member_id = ?
        ORDER BY platforms.name
    """


class Mutation:

    add_platform = """
        INSERT INTO platforms (name, emoji_id)
        VALUES (?,?)
    """

    delete_platform = """
        DELETE FROM platforms
        WHERE id = ?
    """

    register_player = """
        INSERT INTO players (member_id, gamertag, platform_id)
        VALUES (?, ?, ?)
        ON CONFLICT (member_id, platform_id)
            DO UPDATE SET gamertag=excluded.gamertag
    """

    unregister_player = """
        DELETE FROM players
        WHERE member_id = ?
        AND platform_id = ?
    """
