from dataclasses import dataclass
from typing import Dict, List

import aiosqlite
import discord
from discord.ext import commands

from . import sql

DEFAULT_PREFIX = "gdb/"


@dataclass
class Platform(commands.Converter):
    """
    A Dataclass representing platforms

    Attrs:
       id: int
       name: str
       emoji_id: int
    """

    id: int = None
    name: str = None
    emoji_id: int = None

    @staticmethod
    async def convert(ctx: commands.Context, argument: str):
        return ctx.cog.platforms.get(argument.lower())


class GamerDB(commands.Cog):
    def __init__(self, bot) -> None:
        print(f"Loaded cog {__name__}")
        self.bot: commands.Bot = bot
        self.bot.command_prefix = self.get_prefix
        self.platforms: Dict[str, Platform]
        self.bot.loop.create_task(self.connect_and_create())

    async def connect_and_create(self):
        """
        Sets up the database for the cog
        """
        self.db = await aiosqlite.connect("gamerdb.db")
        self.db.row_factory = aiosqlite.Row
        await self.db.execute(sql.CreateTable.players)
        await self.db.execute(sql.CreateTable.platforms)
        await self.db.execute(sql.CreateTable.guilds)
        await self.db.commit()
        await self.cache_platforms()

    async def get_prefix(self, bot: commands.Bot, message: discord.Message):
        prefix = await self.db.execute_fetchall(sql.Query.prefix, (message.guild.id,))
        prefix = prefix[0]["prefix"] if prefix else DEFAULT_PREFIX
        return commands.when_mentioned_or(prefix)(bot, message)

    async def cache_platforms(self):
        """
        Cache platforms to reduce queries
        """
        async with self.db.execute(sql.Query.platforms) as cursor:
            self.platforms = {p["name"]: Platform(*p) for p in await cursor.fetchall()}

    @staticmethod
    def filter_platforms(platforms: List[Platform]) -> List[Platform]:
        """
        Filter out `None` types in greedy platform lists

        Args:
            platforms (List[Platform]): A list of platforms returned from `commands.Greedy` args

        Returns:
            List[Platform]: Cleaned and sorted list of platforms
        """
        return sorted(filter(None, platforms), key=lambda p: p.name)

    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(aliases=["set_prefix"])
    async def setPrefix(self, ctx: commands.Context, prefix: str = DEFAULT_PREFIX):
        """
        Set the prefix the bot will use for your guild.

        Args:
            prefix (str): The new prefix the bot will respond to.
        """
        await self.db.execute(sql.Mutation.register_prefix, (ctx.guild.id, prefix))
        await self.db.commit()
        await ctx.send(f"Prefix for this guild has been set to: **{prefix}**")

    @commands.guild_only()
    @commands.command(name="prefix")
    async def _prefix(self, ctx: commands.Context):
        """
        Get the prefix for this guild.
        """
        prefix = await self.db.execute_fetchall(sql.Query.prefix, (ctx.guild.id,))
        prefix = prefix[0]["prefix"] if prefix else DEFAULT_PREFIX
        await ctx.send(f"The prefix for this guild is: **{prefix}**")

    @commands.guild_only()
    @commands.command()
    async def register(
        self, ctx: commands.Context, username: str, platforms: commands.Greedy[Platform]
    ):
        """
        Register a username with a supported platform

        Usage:
            !register <username> <platform1> <platform2>

        Args:
            username: The in game name you'd like to register
            platforms: A list of approved platform names to add under the username
        """
        platforms = self.filter_platforms(platforms)
        if platforms:
            await self.db.executemany(
                sql.Mutation.register_player,
                [(ctx.author.id, username, platform.id) for platform in platforms],
            )
            await self.db.commit()
            await ctx.send(
                f'{ctx.author.mention}, user info for {", ".join(f"**{platform.name.title()}**" for platform in platforms)} has been registered!'
            )

        else:
            await ctx.send(
                f"{ctx.author.mention}, you didn't enter any valid platforms"
            )

    @commands.guild_only()
    @commands.command()
    async def unregister(
        self, ctx: commands.Context, platforms: commands.Greedy[Platform]
    ):
        """
        Unregister a platform

        Usage:
            !unregister <platform1> <platform2>

        Args:
            platforms: A list of approved platform names to remove from your profile
        """
        platforms = self.filter_platforms(platforms)
        if platforms:
            await self.db.executemany(
                sql.Mutation.unregister_player,
                [(ctx.author.id, platform.id) for platform in platforms],
            )
            await self.db.commit()
            await ctx.send(
                f'{ctx.author.mention}, user info for {", ".join(f"**{platform.name.title()}**" for platform in platforms)} has been unregistered!'
            )

        else:
            await ctx.send(
                f"{ctx.author.mention}, you didn't enter any valid platforms"
            )

    @commands.guild_only()
    @commands.command()
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        """
        View platforms and usernames for a member

        Usage:
            !profile @member

        Args:
            member: The members profile to view. Defaults to the message author.
        """
        member = member or ctx.author
        platforms = await self.db.execute_fetchall(sql.Query.profile, (member.id,))
        embed = discord.Embed(
            title=f"Platform info for {member.display_name}",
            description="No platforms have been added",
            color=discord.Color.purple(),
        )
        embed.set_thumbnail(url=member.avatar_url)
        if platforms:
            embed.description = "\n".join(
                f"**{self.bot.get_emoji(emoji_id)}** | *{platform_name.title()}* | __{username}__"
                for username, platform_name, emoji_id in platforms
            )
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(aliases=["users_for"])
    async def usersFor(self, ctx: commands.Context, platform: Platform):
        """
        Get a list of users that have registered for a platform

        Args:
            platform (Platform): The name of a valid platform
        """
        if not platform:
            return await ctx.send("Missing or invalid platform name!")
        players = [
            f"<@{player['member_id']}> - {player['username']}"
            for player in await self.db.execute_fetchall(
                sql.Query.platform_players, (platform.id,)
            )
            if ctx.guild.get_member(player["member_id"])
        ]
        embed = discord.Embed(color=discord.Color.blurple(),)

        embed.add_field(
            name=self.bot.get_emoji(platform.emoji_id), value="\n".join(players)
        )
        await ctx.send(embed=embed)

    @commands.command(name="platforms")
    async def _platforms(self, ctx):
        """
        View available platforms
        """
        embed = discord.Embed(
            title="Supported Platforms",
            description="\n".join(
                f"{self.bot.get_emoji(platform.emoji_id)}: **{platform.name.title()}**"
                for platform in self.platforms.values()
            ),
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command()
    async def addPlatform(
        self, ctx: commands.Context, platform_name: str, emoji: discord.Emoji
    ):
        """
        Add a platform

        Usage:
            !addPlatform <platform_name> <:custom_emoji:>

        Args:
            platform_name: The name of the platform to add
            emoji: The custom emoji to use for the platform
        """
        platform_name = platform_name.lower()
        await self.db.execute(sql.Mutation.add_platform, (platform_name, emoji.id))
        await self.db.commit()
        await ctx.author.send(
            f"Added platform: **{platform_name}**\nWith Emoji: {emoji}"
        )
        await self.cache_platforms()

    @commands.is_owner()
    @commands.command()
    async def deletePlatform(self, ctx: commands.Context, platform: Platform):
        """
        Delete a platform

        Usage:
            !deletePlatform <platform_name>

        Args:
            platform: The name of the platform to delete
        """
        if platform:
            await self.db.execute(sql.Mutation.delete_platform, (platform.id,))
            await self.db.commit()
            await ctx.author.send(f"Deleted platform: **{platform.name}**")
            await self.cache_platforms()


def setup(bot: commands.Bot):
    bot.add_cog(GamerDB(bot))


def run():
    import os
    import dotenv

    dotenv.load_dotenv()

    bot = commands.Bot(command_prefix="", case_insensitive=True)
    bot.add_cog(GamerDB(bot))

    @bot.event
    async def on_ready():
        print("Started GamerDB!")

    bot.run(os.environ["DISCORD_TOKEN"])
