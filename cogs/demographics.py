import asyncio

import discord
from discord.ext import commands

from .utils import checks
from .utils.db.fields import *
from .utils.messages import MessageBox


class Demographics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        loop = asyncio.get_event_loop()
        loop.create_task(self.setup())
        
    async def setup(self):
        await self.bot.wait_until_ready()
        self.demographics_roles = await self.bot.database.new_table(
            "demographics_roles",
            (
                BigInteger("guild_id"),
                BigInteger("role_id"),
            )
        )
        self.historical_demographics = await self.bot.database.new_table(
            "historical_demographics",
            (
                BigInteger("guild_id"),
                Date("date"),
                Json("data"),
            )
        )
    
    @commands.check(checks.is_admin)
    @commands.command()
    async def trackrole(self, ctx, role: discord.Role):
        deletion = await self.demographics_roles.delete_records(
            guild_id=ctx.guild.id,
            role_id=role.id,
        )
        if deletion == "DELETE 0":
            await self.demographics_roles.new_record(
                guild_id=ctx.guild.id,
                role_id=role.id,
            )
            await ctx.send(embed=MessageBox.confirmed(f"Now tracking {role.mention}"))
        else:
            await ctx.send(embed=MessageBox.warning(f"No longer tracking {role.mention}."))

def setup(bot):
    bot.add_cog(Demographics(bot))
