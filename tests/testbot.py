import os

import dotenv
from discord.ext import commands

dotenv.load_dotenv()

bot = commands.Bot(command_prefix=os.environ["COMMAND_PREFIX"], case_insensitive=True)

bot.load_extension("gamerdb.gamerdb")


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}\nBot ID: {bot.user.id}")


bot.run(os.environ["DISCORD_TOKEN"])