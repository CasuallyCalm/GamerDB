from typing import Dict, List
import aiosqlite
import discord
from discord.ext import commands
from dataclasses import dataclass

from . import sql


@dataclass
class Platform(commands.Converter):
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
        self.platforms: Dict[str, Platform]
        self.bot.loop.create_task(self.connect_and_create())

    async def connect_and_create(self):
        self.db = await aiosqlite.connect("gamerdb.db")
        self.db.row_factory = aiosqlite.Row
        await self.db.execute(sql.CreateTable.players)
        await self.db.execute(sql.CreateTable.platforms)
        await self.db.commit()
        await self.cache_platforms()

    async def cache_platforms(self):
        async with self.db.execute(sql.Query.platforms) as cursor:
            self.platforms = {p["name"]: Platform(*p) for p in await cursor.fetchall()}

    @staticmethod
    def filter_platforms(platforms: List[Platform]) -> List[Platform]:
        return sorted(filter(None, platforms), key=lambda p: p.name)

    @commands.guild_only()
    @commands.command()
    async def register(
        self, ctx: commands.Context, gamertag: str, platforms: commands.Greedy[Platform]
    ):
        platforms = self.filter_platforms(platforms)
        if platforms:
            await self.db.executemany(
                sql.Mutation.register_player,
                [(ctx.author.id, gamertag, platform.id) for platform in platforms],
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
        member = member or ctx.author
        profiles = await self.db.execute_fetchall(sql.Query.profile, (member.id,))
        embed = discord.Embed(
            title=f"Platform info for {member.display_name}",
            description="No platforms have been added",
            color=discord.Color.purple(),
        )
        embed.set_thumbnail(url=member.avatar_url)
        if profiles:
            embed.description = "\n".join(
                f"**{self.bot.get_emoji(emoji_id)}** | *{platform_name.title()}* | __{gamertag}__"
                for gamertag, platform_name, emoji_id in profiles
            )
        await ctx.send(embed=embed)

    @commands.command(name="platforms")
    async def _platforms(self, ctx, platform: Platform = None):
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
        if platform:
            await self.db.execute(sql.Mutation.delete_platform, (platform.id,))
            await self.db.commit()
            await ctx.author.send(f"Deleted platform: **{platform.name}**")
            await self.cache_platforms()


def setup(bot: commands.Bot):
    bot.add_cog(GamerDB(bot))
