from discord.ext import commands
from cogs.utils.db import Database
from cogs.utils.db.fields import *


class WaffleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?")
        self.database = Database("postgres://postgres:pass@127.0.0.1:5432/wafflebot")
        self.load_extension("cogs.general")
        self.load_extension("cogs.admin")

    async def on_connect(self):
        await self.database.connect()


with open("token.txt") as f:
    token = f.read().strip()

bot = WaffleBot()
bot.run(token)
