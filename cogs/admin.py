import asyncio
import datetime
import typing

import discord
from discord.ext import commands

from .utils import checks, db, delay
from .utils.db.database import DBFilter
from .utils.db.fields import *
from .utils.logging import ChannelLogger
from .utils.messages import send_embed, Duration

modlogger = ChannelLogger("moderation_log")


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🔨"

    @commands.Cog.listener()
    async def on_ready(self):
        self.infractions = await self.bot.database.new_table(
            "infraction",
            (
                SerialIdentifier(),
                BigInteger("guild_id"),
                BigInteger("member_id"),
                BigInteger("author_id"),
                Text("type"),
                Timestamp("issue_date"),
                Timestamp("expiry_date"),
                Boolean("completed", default="FALSE"),
            ),
        )

        records = await self.infractions.filter(
            where=DBFilter(expiry_date__ne=None, completed=False)
        )
        for record in records:
            guild = self.bot.get_guild(int(record["guild_id"]))
            if record["type"] == "ban":
                user = discord.Object(id=int(record["member_id"]))
                delay.start_waiting(date=record["expiry_date"], callback=self.unban_user, args=(guild, user))
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        mute_role = await db.extras.get_role(self.bot.database, channel.guild, "mute_role")
        if mute_role:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)

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

    @commands.command()
    async def muterole(self, ctx, role: discord.Role = None):
        """Display or set the Mute role."""
        if role:
            await db.extras.set_mute_role(ctx, role)
            await send_embed(ctx.channel, f"{role.mention} is now the Mute role.")

            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)

        else:
            mute_role = await db.extras.get_mute_role(ctx)
            if mute_role:
                await send_embed(ctx.channel, f"{mute_role.mention} is the Mute role.")
            else:
                await send_embed(ctx.channel, f"You have not set an Mute role.")

    @modlogger.log_action
    @commands.command()
    async def ban(self, ctx, member: discord.Member, duration: typing.Optional[Duration] = None, *, reason=None):
        """Ban a member of the server."""
        checks.can_modify_member(ctx, member)

        await member.send(f"🔨 You have been banned from {ctx.guild.name}. Reason: {reason}")
        await member.ban(reason=reason)
        await send_embed(ctx.channel, f"🔨 {member.mention} has been banned. Reason: {reason}")
        
        if duration:
            expiry_date = datetime.datetime.now() + duration
            delay.start_waiting(date=expiry_date, callback=self.unban_user, args=(ctx.guild, member))
        else:
            expiry_date = None

        await self.infractions.new_record(
            guild_id=ctx.guild.id,
            member_id=member.id,
            author_id=ctx.author.id,
            type="ban",
            issue_date=datetime.datetime.now(),
            expiry_date=expiry_date,
        )

        


    async def unban_user(self, guild, user):
        """Unban a user from a guild."""
        await guild.unban(user)
        await self.infractions.update_records(where=DBFilter(member_id=user.id), completed=True)

    @modlogger.log_action
    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        checks.can_modify_member(ctx, member)
        await member.send(f"👢 You have been kicked from {ctx.guild.name}. Reason: {reason}")
        await member.kick(reason=reason)
        await send_embed(ctx.channel, f"👢 {member.mention} has been kicked. Reason: {reason}")
        await self.infractions.new_record(
            guild_id=ctx.guild.id,
            member_id=member.id, 
            author_id=ctx.author.id,
            type="kick",
            issue_date=datetime.datetime.now()
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🚔"

    @commands.Cog.listener()
    async def on_ready(self):
        self.infractions = self.bot.database.table("infraction")

    async def cog_check(self, ctx):
        if ctx.author == ctx.guild.owner:
            return True

        mod_role = await db.extras.get_mod_role(ctx)
        if mod_role:
            return ctx.author.top_role >= mod_role
    
    @modlogger.log_action
    @commands.command()
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        """Warn a member of the server."""
        checks.can_modify_member(ctx, member)
        await self.infractions.new_record(
            guild_id=ctx.guild.id,
            member_id=member.id,
            author_id=ctx.author.id,
            type="warn",
            issue_date=datetime.datetime.now()
        )
        await send_embed(ctx.channel, f"⚠️ {member.mention} has been warned. Reason: {reason}")


def setup(bot):
    bot.add_cog(Admin(bot))
    bot.add_cog(Moderation(bot))
