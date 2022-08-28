import contextlib
import os

import dotenv
import discord
from discord import app_commands
from discord.ext import commands

dotenv.load_dotenv("./tests/.env")

intents= discord.Intents.all()

class TestBot(commands.Bot):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.test_guild = discord.Object(id=os.environ.get('GUILD_ID'))
        self.extension_path='gamerdb.gamerdb'

    async def setup_hook(self) -> None:
        await self.load()
        print(f"Logged in as: {self.user}\nBot ID: {self.user.id}")

    async def load(self):
        await self.load_extension(self.extension_path)
        self.tree.copy_global_to(guild=self.test_guild)
        await self.tree.sync(guild=self.test_guild)
    
bot = TestBot(commands.when_mentioned, intents=intents)

@bot.tree.command()
async def reload(interaction: discord.Interaction):
    client = interaction.client
    with contextlib.suppress(Exception):
        await client.unload_extension(client.extension_path)
    await client.load()
    await interaction.response.send_message('reloaded', ephemeral=True)

def run():
    bot.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    run()
