import asyncio

import discord
from discord.ext import commands

from .utils.logging import ChannelLogger
from .utils import db
from .utils.db.fields import *
from .utils import checks
from .utils.messaging import send_embed


modlogger = ChannelLogger("moderation_log")


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.database.new_table("warning",
            (
                BigInteger("member_id"),
                BigInteger("author_id"),
                Text("reason"),
                Timestamp("timestamp"),
            ),
        )
    
    async def cog_check(self, ctx):
        if ctx.author == ctx.guild.owner:
            return True

        admin_role = await db.extras.get_admin_role(ctx)
        if admin_role:
            return ctx.author.top_role >= admin_role

    @commands.command()
    async def modlog(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to send mod logs to."""
        if channel is None:
            channel = await modlogger.get_channel(ctx)
            if channel is None:
                await send_embed(ctx.channel, "You have not set a moderation log channel yet on this server!")
            else:
                await send_embed(ctx.channel, f"{channel.mention} is the moderation log channel.")
        else:
            await modlogger.set_channel(ctx, channel)
            await send_embed(ctx.channel, f"{channel.mention} is now the moderation log.")

    @commands.command()
    @commands.is_owner()
    async def adminrole(self, ctx, role: discord.Role = None):
        """Display or set the Administrator role."""
        if role:
            await db.extras.set_admin_role(ctx, role)
            await send_embed(ctx.channel, f"{role.mention} is now the Administrator role.")
        else:
            admin_role = await db.extras.get_admin_role(ctx)
            if admin_role:
                await send_embed(ctx.channel, f"{admin_role.mention} is the Administrator role.")
            else:
                await send_embed(ctx.channel, f"You have not set an Administrator role.")

    @commands.command()
    async def modrole(self, ctx, role: discord.Role = None):
        """Display or set the Moderator role."""
        if role:
            await db.extras.set_mod_role(ctx, role)
            await send_embed(ctx.channel, f"{role.mention} is now the Moderator role.")
        else:
            mod_role = await db.extras.get_mod_role(ctx)
            if mod_role:
                await send_embed(ctx.channel, f"{mod_role.mention} is the Moderator role.")
            else:
                await send_embed(ctx.channel, f"You have not set an Moderator role.")

    @modlogger.log_action
    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member of the server."""
        checks.can_modify_member(ctx, member)
        await member.send(f"🔨 You have been banned from {ctx.guild.name}. Reason: {reason}")
        await member.ban(reason=reason)
        await send_embed(
            ctx.channel, "🔨 {member.name} has been banned by {ctx.author.mention}. Reason: {reason}"
        )

    @modlogger.log_action
    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        checks.can_modify_member(ctx, member)
        await member.send(f"👢 You have been kicked from {ctx.guild.name}. Reason: {reason}")
        await member.kick(reason=reason)
        await send_embed(
            ctx.channel, "👢 {member.name} has been kicked by {ctx.author.mention}. Reason: {reason}"
        )


def setup(bot):
    bot.add_cog(Admin(bot))
