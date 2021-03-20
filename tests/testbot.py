import os

import dotenv
import discord
from discord.ext import commands

dotenv.load_dotenv("./tests/.env")

bot = commands.Bot(
    command_prefix="!", case_insensitive=True, intents=discord.Intents.all()
)

bot.load_extension("gamerdb.gamerdb")


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}\nBot ID: {bot.user.id}")


def run():
    bot.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    run()
