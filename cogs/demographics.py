import asyncio
from itertools import groupby
import datetime
import logging
from io import BytesIO

import discord
from discord.ext import commands, tasks
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from .utils import checks
from .utils.db.fields import *
from .utils.db.database import DBFilter
from .utils.messages import MessageBox


class Demographics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "📊"
        self.logger = logging.getLogger(__name__)

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
                BigInteger("role_id"),
                Integer("member_count"),
            )
        )
        self.record_demographics.start()
    
    @tasks.loop(hours=24, reconnect=True)
    async def record_demographics(self):
        today = datetime.date.today()
        records_today = await self.historical_demographics.filter(
            where=DBFilter(date=today), limit=1
        )
        if not records_today:
            self.logger.info("Recording demographic role changes")
            records = await self.demographics_roles.all(order_by="guild_id")
            for record in records:
                guild = self.bot.get_guild(record["guild_id"])
                member_count = len(guild.get_role(record["role_id"]).members)
                await self.historical_demographics.new_record(
                    guild_id=record["guild_id"],
                    date=today,
                    role_id=record["role_id"],
                    member_count=member_count,
                )
            self.logger.info("Complete")

    @commands.check(checks.is_admin)
    @commands.command()
    async def trackrole(self, ctx, *, role: discord.Role):
        """Begin tracking the demographics of a role."""
        status = await self.demographics_roles.delete_records(
            where=DBFilter(
                guild_id=ctx.guild.id,
                role_id=role.id,
            )
        )
        if status == "DELETE 0":
            await self.demographics_roles.new_record(
                guild_id=ctx.guild.id,
                role_id=role.id,
            )
            await ctx.send(embed=MessageBox.confirmed(f"Now tracking {role.mention}"))
        else:
            await ctx.send(embed=MessageBox.confirmed(f"No longer tracking {role.mention}."))

    @commands.check(checks.is_admin)
    @commands.command()
    async def tracking(self, ctx):
        """Get the list of roles which are currently being tracked."""
        role_records = await self.demographics_roles.filter(
            where=DBFilter(guild_id=ctx.guild.id)
        )
        if role_records:
            roles = [ctx.guild.get_role(r["role_id"]) for r in role_records]
            mentions = [r.mention for r in sorted(roles, reverse=True)]
            await ctx.send(embed=MessageBox.info("You are tracking the following roles\n_ _" + "\n".join(mentions)))
        else:
            await ctx.send(embed=MessageBox.info("You are not tracking any roles on this server."))

    @commands.command()
    async def demographics(self, ctx):
        """View the server's demographics in a graph."""
        role_records = await self.demographics_roles.filter(
            where=DBFilter(guild_id=ctx.guild.id)
        )
        roles = [ctx.guild.get_role(r["role_id"]) for r in role_records]
        graph = await self.get_current_demographics_graph(ctx.guild, roles)
        await ctx.send(file=discord.File(graph, filename="demographics.png"))
    
    async def get_current_demographics_graph(self, guild, roles):
        """Create a graph of demographics for a guild for specified roles."""
        roles.sort()
        names = [r.name for r in roles]
        colours = [tuple([c / 255 for c in r.colour.to_rgb()]) for r in roles]
        numbers = [len(r.members) for r in roles]

        plt.style.use("dark_background")
        fig = plt.figure()

        x = names
        y = numbers
        x_pos = [i for i, _ in enumerate(x)]

        ax = fig.add_subplot(111)

        ax.set_title(f"Demographics for {guild.name}")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.bar(x_pos, y, color=colours, edgecolor=colours)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x, rotation=20)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_ticks_position("left")
        ax.xaxis.set_ticks_position("bottom")

        fig.tight_layout()

        image = BytesIO()
        fig.savefig(image, format="png", transparent=True)
        image.seek(0)
        return image


def setup(bot):
    bot.add_cog(Demographics(bot))
