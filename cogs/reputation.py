import discord
from discord.ext import commands

from .utils.db.fields import *
from .utils.db.database import DBFilter
from .utils.messages import MessageBox
from .utils import checks

import asyncio

class Reputation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🥇"
        loop = asyncio.get_event_loop()
        loop.create_task(self.setup())
        
    async def setup(self):
        await self.bot.wait_until_ready()
        self.reputation = await self.bot.database.new_table(
            "reputation",
            (
                BigInteger("guild_id"),
                BigInteger("member_id"),
                Integer("points"),
            )
        )

    @commands.command()
    async def rep(self, ctx, member: discord.Member):
        """Add a reputation point to a member."""
        checks.member_is_other(ctx, member)
        where_sql, where_values = DBFilter(guild_id=ctx.guild.id, member_id=member.id).sql()
        reps = await self.bot.database.execute_sql(
            f"UPDATE reputation SET points = points + 1 {where_sql} RETURNING points",
            *where_values,
            fetch=True
        )
        if not reps:
            await self.reputation.new_record(guild_id=ctx.guild.id, member_id=member.id, points=1)
            reps = 1
        else:
            reps = reps[0]["points"]
        
        await ctx.send(embed=MessageBox.success(f"{member.mention} now has `{reps}` reputation points."))

    @commands.command()
    async def leaderboard(self, ctx):
        """Displays the server reputation leaderboard."""
        scores = await self.reputation.filter(
            where=DBFilter(guild_id=ctx.guild.id),
            order_by="points",
            desc=True
        )
        top10 = []
        i = 0
        while len(top10) < 10 and i < len(scores):
            record = scores[i]
            if member := ctx.guild.get_member(int(record["member_id"])):
                top10.append((member, record["points"]))
            i += 1
        embed = discord.Embed(colour=0xffb636)
        embed.set_author(name="Reputation Leaderboard", icon_url="https://i.imgur.com/wreHU7E.png")
        for member, reps in top10:
            embed.add_field(name=member.display_name, value=reps)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Reputation(bot))
