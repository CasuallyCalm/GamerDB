from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import aiosqlite
import discord
from discord import Emoji, app_commands
from discord.ext import commands
from discord.ui import Select, View

from . import sql

@dataclass
class Platform:
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

class _PlatformTransformer(app_commands.Transformer):
    def __init__(self, platforms: Dict[str,Platform] = None) -> None:
        if platforms is None:
            platforms = {}
        self.platforms = platforms
    
    async def transform(self, interaction: discord.Interaction, value: str) -> Platform:
        if users:=self.platforms.get(value):
            return users

        raise app_commands.TransformerError(value, Platform, self)
    
    async def autocomplete(self, interaction: discord.Interaction, value: str):
        return [discord.app_commands.Choice(name=platform.title(), value=platform) for platform in self.platforms if value.lower() in platform.lower()]


PlatformTransformer=_PlatformTransformer()

class EmojiTransformer(app_commands.Transformer):

    async def transform(self, interaction: discord.Interaction, value: str) -> Emoji:
        ctx = await commands.Context.from_interaction(interaction)
        return await commands.converter.EmojiConverter().convert(ctx, value)


class RegisterView(View):

    def __init__(self, username: str, db: aiosqlite.Connection, options: List[discord.SelectOption]):
        super().__init__()
        self.username =  username
        self.db = db
        self.options = options
        self.platform_select.max_values=len(options)
        for option in options:
            self.platform_select.append_option(option)

    @discord.ui.select(placeholder="Select Platforms to Register...")
    async def platform_select(self, interaction: discord.Interaction, select: Select):
        await self.db.executemany(
            sql.Mutation.register_player,
            [( interaction.user.id, self.username, int(platform_id)) for platform_id in select.values],
        )
        await self.db.commit()
        await interaction.response.send_message(
            f'{interaction.user.mention}, the selected platform(s) have been registered for **{self.username}**!',
            ephemeral=True
        )

class UnRegisterView(View):

    def __init__(self, db: aiosqlite.Connection, options: List[discord.SelectOption]):
        super().__init__()
        self.db = db
        self.options = options
        self.platform_select.max_values=len(options)
        for option in options:
            self.platform_select.append_option(option)

    @discord.ui.select(placeholder="Select Platforms to Unregister...")
    async def platform_select(self, interaction: discord.Interaction, select: Select):
        await self.db.executemany(
            sql.Mutation.unregister_player,
            [(interaction.user.id, int(platform_id)) for platform_id in select.values],
        )
        await self.db.commit()
        
        await interaction.response.send_message(f'{interaction.user.mention}, the selected platform(s) have been unregistered!', ephemeral=True)

def is_owner():
    """
    Checks if the person who used the command is the bot owner
    """
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == interaction.client.application.owner.id
    return app_commands.check(predicate)


@app_commands.guild_only()
class GamerDB(commands.GroupCog, name="gdb"):

    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args,  **kwargs)
        print(f"Loaded cog {__name__}")
        self.bot= bot
        self.db: aiosqlite.Connection
        self.platforms: Dict[str, Platform]
    
    async def cog_load(self) -> None:
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
    
    async def cog_unload(self) -> None:
        """
        Disconnect from the database on cog unload
        """
        await self.db.close()

    async def cache_platforms(self):
        """
        Cache platforms to reduce queries
        """
        async with self.db.execute(sql.Query.platforms) as cursor:
            self.platforms = {p["name"]: Platform(*p) for p in await cursor.fetchall()}
        PlatformTransformer.platforms= self.platforms

    
    async def get_platform_options(self, user: Union[discord.User, discord.Member]=None) -> List[discord.SelectOption]:
        """
        Create a list of discord SelectionOptions to select platforms for views

        Args:
            user (Union[discord.User, discord.Member], optional): Get the platforms a user is currently registered for. Defaults to None.

        Returns:
            List[discord.SelectOption]: List of options to user for select menus in Views
        """
        platforms:List[Platform] = self.platforms.values()
        if user:
            platforms = [Platform(*_platform) for _platform in await self.db.execute_fetchall(sql.Query.player_platforms, (user.id,))]

        return [discord.SelectOption(label=platform.name.title(), value=platform.id, emoji=self.bot.get_emoji(platform.emoji_id)) for platform in platforms]

    @app_commands.guild_only()
    @app_commands.command()
    async def register(self, interaction: discord.Interaction, username: str):
        """
        Register a username with a supported platform

        Args:
            username (str): The in-game-name/gamertag you want to register
        """

        view = RegisterView(username=username, db=self.db, options= await self.get_platform_options())
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command()
    async def unregister(self, interaction: discord.Interaction):
        """
        Unregister from a platform or platforms
        """
        if user_platform_options := await self.get_platform_options(interaction.user):
            view=UnRegisterView(db=self.db, options=user_platform_options)
            return await interaction.response.send_message(view=view, ephemeral=True)

        await interaction.response.send_message(f"{interaction.user.mention}, you're not registered for any platforms!", ephemeral=True)


    @app_commands.guild_only()
    @app_commands.command()
    async def profile(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """
        View platforms and usernames for a member or yourself

        Usage:
            !profile @member

        Args:
            member: The members profile to view. Defaults to the message author.
        """
        member = member or interaction.user
        platforms = await self.db.execute_fetchall(sql.Query.profile, (member.id,))
        embed = discord.Embed(
            title=f"Platform info for {member.display_name}",
            description="No platforms have been added",
            color=discord.Color.purple(),
        )
        embed.set_thumbnail(url=member.avatar.url)
        if platforms:
            embed.description = "\n".join(
                f"**{self.bot.get_emoji(emoji_id)}** | *{platform_name.title()}* | __{username}__"
                for username, platform_name, emoji_id in platforms
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.guild_only()
    @app_commands.command(name='users-for')
    async def users_for(self, interaction: discord.Interaction, platform: app_commands.Transform[Platform, PlatformTransformer]):
        """
        Get a list of users that have registered for a platform

        Args:
            platform (Platform): The name of a valid platform
        """
        players = [f"<@{player['member_id']}> - {player['username']}" for player in await self.db.execute_fetchall(sql.Query.platform_players, (platform.id,)) if interaction.guild.get_member(player["member_id"])]

        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f"{self.bot.get_emoji(platform.emoji_id)} Members of {interaction.guild.name} who have registered with {platform.name.title()}"

        embed.add_field(name="Registered", value="\n".join(players) if players else "*empty*")

        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="platforms")
    async def _platforms(self, interaction: discord.Interaction):
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
        await interaction.response.send_message(embed=embed)

    @is_owner()
    @app_commands.guild_only()
    @app_commands.command(name="add-platform")
    @app_commands.rename(platform_name="platform-name")
    async def add_platform(self, interaction: discord.Interaction, platform_name: str, emoji: app_commands.Transform[Emoji,EmojiTransformer]):
        """
        (Bot Owner Only) Add a platform 

        Usage:
            !addPlatform <platform_name> <:custom_emoji:>

        Args:
            platform_name: The name of the platform to add
            emoji: The custom emoji to use for the platform
        """
        platform_name = platform_name.lower()
        await self.db.execute(sql.Mutation.add_platform, (platform_name, emoji.id))
        await self.db.commit()
        await interaction.response.send_message(
            f"Added platform: **{platform_name.title()}**\nWith Emoji: {emoji}",
            ephemeral=True
        )
        await self.cache_platforms()

    @is_owner()
    @app_commands.command(name='delete-platform')
    async def delete_platform(self, interaction: discord.Interaction, platform: app_commands.Transform[Platform, PlatformTransformer]):
        """
        (Bot Owner Only) Delete a platform

        Usage:
            !deletePlatform <platform_name>

        Args:
            platform: The name of the platform to delete
        """
        if platform:
            await self.db.execute(sql.Mutation.delete_platform, (platform.id,))
            await self.db.commit()
            await interaction.response.send_message(f"Deleted platform: **{platform.name}**", ephemeral=True)
            await self.cache_platforms()

    @users_for.error
    @delete_platform.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """
        Handle errors when getting an invalid platform entry

        Args:
            interaction (discord.Interaction): The discord interaction to reference
            error (app_commands.AppCommandError): The base error for an the app command
        """
        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(f'{interaction.user.mention}, **{error.value}** is an invalid platform', ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GamerDB(bot=bot))


class GamerBot(commands.Bot):

    async def setup_hook(self) -> None:
       await self.add_cog(GamerDB(self))
       print("Started GamerDB!")
    

def run():
    import os

    import dotenv

    dotenv.load_dotenv()

    intents = discord.Intents.default()
    bot = GamerBot(commands.when_mentioned, intents=intents)

    bot.run(os.environ["DISCORD_TOKEN"])
