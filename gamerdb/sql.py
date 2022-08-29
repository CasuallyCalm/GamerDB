class CreateTable:

    players = """
        CREATE TABLE IF NOT EXISTS players (
          id INTEGER PRIMARY KEY,
          member_id INTEGER NOT NULL,
          username TEXT NOT NULL,
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

    guilds = """
        CREATE TABLE IF NOT EXISTS guilds (
          id INTEGER PRIMARY KEY,
          prefix TEXT NOT NULL
        );
        """


class Query:

    platforms = """
        SELECT * FROM platforms
        ORDER BY platforms.name
    """

    profile = """
        SELECT players.username, platforms.name, platforms.emoji_id
        FROM players
        JOIN platforms
        ON players.platform_id = platforms.id
        AND players.member_id = ?
        ORDER BY platforms.name
    """

    player_platforms = """
        SELECT platforms.id, platforms.name, platforms.emoji_id
        FROM players
        JOIN platforms
        ON players.platform_id = platforms.id
        AND players.member_id = ?
        ORDER BY platforms.name
    """

    platform_players = """
    SELECT member_id, username
    FROM players
    JOIN platforms
    ON players.platform_id = platforms.id
    WHERE platforms.id = ?
    """

    prefix = """
        SELECT prefix
        FROM guilds
        WHERE id = ?
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
        INSERT INTO players (member_id, username, platform_id)
        VALUES (?, ?, ?)
        ON CONFLICT (member_id, platform_id)
            DO UPDATE SET username=excluded.username
    """

    unregister_player = """
        DELETE FROM players
        WHERE member_id = ?
        AND platform_id = ?
    """

    register_prefix = """
        INSERT INTO guilds (id, prefix)
        VALUES (?, ?)
        ON CONFLICT (id)
            DO UPDATE SET prefix=excluded.prefix
    """