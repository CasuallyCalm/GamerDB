import re
import dataset
import discord
from discord.ext import commands
from jthon import Jthon


TOKEN = Jthon('token', ['your discord token'])
TOKEN.save()


invite_link = 'https://discordapp.com/api/oauth2/authorize?client_id={}&permissions=264192&scope=bot'
prefix = 'gdb/'
bot = commands.Bot(command_prefix=commands.when_mentioned_or(prefix), case_insensitive=True, pm_help=True)
bot.activity = discord.Game(name=f'{prefix}help')

# platform schema
default_schema = {"platform": {
    "emoji": 'custom emoji ID#',
    "link": None
}}

used_platforms = Jthon('platforms', default_schema)


db = dataset.connect('sqlite:///gdb.db')
table = db.get_table('database')


def check_table():
    if 'player' not in table.columns:
        table.create_column('player', dataset.types.Integer)
    for platform in used_platforms.data:
        if platform not in table.columns:
            table.create_column(platform, dataset.types.UnicodeText)


check_table()


def check_emoji(guild, platform):
    bot_user = guild.get_member(bot.user.id)
    if not bot_user.guild_permissions.external_emojis:
        return platform.title()
    return bot.get_emoji(used_platforms.data.get(platform).get("emoji"))


class checkMember(commands.MemberConverter):
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        guild = ctx.guild
        result = None
        if match is None:
            return 'not_found'
        user_id = int(match.group(1))
        if guild:
            result = guild.get_member(user_id)
        return result


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')
    print(f'Invite Link: {invite_link.format(bot.user.id)}')


class GamerDB(commands.Cog):

    def __init__(self, bot_instance):
        self.bot = bot_instance

    @commands.command(aliases=['add'])
    async def register(self, ctx, player_identifier, *platforms):
        ''': Register supported platforms with your username or platform ID
            usage: gdb/register <username/id> origin steam # this would register a common username or id with Origin and Steam
        '''
        added = dict((platform.lower(), player_identifier) for platform in platforms if platform.lower() in used_platforms.data)
        if added:
            added.update({"player": ctx.author.id})
            table.upsert(added, ['player'])
            await ctx.send(f'{ctx.author.mention}, user info for {", ".join(f"**{platform.title()}**" for platform in added if platform != "player")} has been added!')
        else:
            await ctx.send(f"{ctx.author.mention}, you didn't enter any valid platforms")

    @commands.command(aliases=['remove'])
    async def unregister(self, ctx, *platforms):
        ''': Unregister supported platforms
            usage: gdb/unregister origin steam # this would register your profile with Origin and Steam
        '''
        added = dict((platform.lower(), '') for platform in platforms if platform.lower() in used_platforms.data)
        if added:
            added.update({"player": ctx.author.id})
            table.upsert(added, ['player'])
            await ctx.send(f'{ctx.author.mention}, user info for {", ".join(f"**{platform.title()}**" for platform in added if platform != "player")} has been removed!')
        else:
            await ctx.send(f"{ctx.author.mention}, you didn't enter any valid platforms")

    @commands.command(aliases=['lookup'])
    async def profile(self, ctx, player: checkMember= None):
        ''': View your profile or mention someone to see theirs
            usage: gdb/profile # this would show your profile
                gdb/profile @member # this would show the profile of a mentioned user
        '''
        if player == 'not_found':
            await ctx.send(f'{ctx.author.mention}, @ someone to get their profile.')
        else:
            if not player:
                player = ctx.author
            info = table.find_one(player=player.id)
            embed = discord.Embed(title=f"Platform info for {player.name}", description='No platforms have been added', color=discord.Color.purple())
            embed.set_thumbnail(url=player.avatar_url)
            if info:
                description = '\n'.join(f'**{check_emoji(ctx.guild,platform)}**: {user}' for platform, user in info.items() if platform in used_platforms.data and user)
                if description:
                    embed.description = description
            await ctx.send(embed=embed)

    @commands.command(name='platforms')
    async def _platforms(self, ctx):
        ''': A list of currently supported platforms
            usage: gdb/platforms # returns a list of supported platforms
        '''
        embed = discord.Embed(title='Supported Platforms', description='\n'.join(
            f"{check_emoji(ctx.guild,platform)}: **{platform.title()}**" for platform in used_platforms.data if platform != "player"), color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx):
        ''': Add me to your server!
        '''
        await ctx.author.send(invite_link.format(self.bot.user.id))


bot.add_cog(GamerDB(bot))

bot.run(TOKEN.data[0])
