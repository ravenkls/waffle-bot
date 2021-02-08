from discord.ext import commands
import asyncio


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = ""

        loop = asyncio.get_event_loop()
        loop.create_task(self._setup())

    async def _setup(self):
        await self.bot.wait_until_ready()
        await self.setup()

    async def setup(self):
        pass