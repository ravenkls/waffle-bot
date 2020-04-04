from discord.ext import commands
from cogs.utils.db import Database
from cogs.utils.db.fields import *
import logging


class WaffleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?")
        self.database = Database("postgres://postgres:pass@127.0.0.1:5432/wafflebot")
        self.load_extension("cogs.general")
        self.load_extension("cogs.admin")
        self.logger = logging.getLogger(__name__)

    async def on_connect(self):
        await self.database.connect()

    async def on_ready(self):
        self.logger.info("Bot is ready and accepting commands.")


if __name__ == "__main__":
    with open("token.txt") as f:
        token = f.read().strip()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] [%(name)s] %(message)s")
    bot = WaffleBot()
    bot.run(token)
