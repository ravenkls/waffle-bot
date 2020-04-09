import asyncio
from itertools import groupby
import datetime
import logging
from io import BytesIO
from collections import defaultdict

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
            await ctx.send(embed=MessageBox.info("The following roles are being tracked on this server\n\n" + "\n".join(mentions)))
        else:
            await ctx.send(embed=MessageBox.info("No roles are being tracked on this server."))

    @commands.command()
    async def demographics(self, ctx):
        """View the server's demographics in a graph."""
        role_records = await self.demographics_roles.filter(
            where=DBFilter(guild_id=ctx.guild.id)
        )
        roles = [ctx.guild.get_role(r["role_id"]) for r in role_records]
        graph = await self.get_current_demographics_graph(ctx.guild, roles)
        await ctx.send(file=discord.File(graph, filename="demographics.png"))
    
    @commands.command(aliases=["history"])
    async def demographicshistory(self, ctx):
        """Display the historical data of the server's demographics in a graph."""
        role_records = await self.demographics_roles.filter(
            where=DBFilter(guild_id=ctx.guild.id)
        )
        tracked_role_ids = [role["role_id"] for role in role_records]
        
        if not tracked_role_ids:
            return await ctx.send(embed=MessageBox.info("No roles are being tracked on this server."))

        historical_records = await self.historical_demographics.filter(
            where=DBFilter(guild_id=ctx.guild.id, role_id__in=tracked_role_ids),
            order_by="date",
        )

        graph = await self.get_historical_demographics_graph(ctx.guild, historical_records)
        await ctx.send(file=discord.File(graph, filename="history.png"))

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

    async def get_historical_demographics_graph(self, guild, records):
        """Create a graph of the historical demographics for a guild given records."""
        plt.style.use("dark_background")
        fig = plt.figure()

        ax = fig.add_subplot(111)

        ax.set_title(f"Historical Demographics for {guild.name}")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        role_data = defaultdict(list)
        for date, records in groupby(records, lambda x: x["date"]):
            for record in records:
                role_name = guild.get_role(record["role_id"]).name
                role_data[role_name].append((date, record["member_count"]))
        
        for label, data in role_data.items():
            xs = [d[0] for d in data]
            ys = [d[1] for d in data]
            plt.plot(xs, ys, label=label)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_ticks_position("left")
        ax.xaxis.set_ticks_position("bottom")
        ax.legend(frameon=False)

        fig.tight_layout()

        image = BytesIO()
        fig.savefig(image, format="png", transparent=True)
        image.seek(0)
        return image


def setup(bot):
    bot.add_cog(Demographics(bot))
