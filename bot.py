import logging
import os
import sys
import configparser

from discord.ext import commands

from cogs.utils.db import Database
from cogs.utils.db.fields import *


class WaffleBot(commands.Bot):
    def __init__(self, database_url):
        super().__init__(command_prefix="-")
        self.database_url = database_url
        self.database = Database(self.database_url)
        self.load_extension("cogs.general")
        self.load_extension("cogs.admin")
        self.load_extension("cogs.reputation")
        self.logger = logging.getLogger(__name__)

    async def on_connect(self):
        await self.database.connect()

    async def on_ready(self):
        self.logger.info("Bot is ready and accepting commands.")


def generate_settings():
    config = configparser.ConfigParser()
    config["BotSettings"] = {"token": "", "database_url": ""}
    with open("settings.cfg", "w") as f:
        config.write(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] [%(name)s] %(message)s")

    if not os.path.exists("settings.cfg"):
        generate_settings()
        logging.critical("No config found. generating 'settings.cfg', please fill "
                         "in the required settings before running the bot")
        sys.exit()
    
    config = configparser.ConfigParser()
    config.read("settings.cfg")
    try:
        token = config["BotSettings"]["token"]
        database_url = config["BotSettings"]["database_url"]
    except (configparser.NoSectionError, KeyError):
        logging.critical("Malformed 'settings.cfg' file, please fix this before running the bot.")
        sys.exit()

    bot = WaffleBot(database_url)
    bot.run(token)
