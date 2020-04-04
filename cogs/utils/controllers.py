import asyncio
import inspect
from collections import defaultdict
from datetime import datetime

import discord

from . import delay
from . import db
from .db.database import DBFilter
from .db.fields import *


class ChannelLogger:
    """Controls logging to a channel."""

    def __init__(self, name):
        self.name = name

    def log_action(self, command):
        command.after_invoke(self.send_command_log)
        return command

    async def set_channel(self, ctx, channel):
        await ctx.bot.database.set_setting(channel.guild, self.name, channel.id)

    async def get_channel(self, ctx):
        channel_id = await ctx.bot.database.get_setting(ctx.guild, self.name)
        if channel_id:
            return ctx.guild.get_channel(int(channel_id))

    async def send_command_log(self, cog, ctx):
        if ctx.command_failed:
            return

        channel = await self.get_channel(ctx)
        embed = discord.Embed(
            title=ctx.bot.command_prefix + ctx.command.name,
            description=f"[Jump to message]({ctx.message.jump_url})",
            timestamp=datetime.now(),
        )
        embed.add_field(name="Moderator", value=ctx.author.mention)

        arg_names = ctx.command.clean_params.keys()
        arg_values = ctx.args[2:] + list(ctx.kwargs.values())

        for arg_name, arg_value in zip(arg_names, arg_values):
            arg_name = arg_name.replace("_", " ").title()
            if (
                isinstance(arg_value, discord.Member)
                or isinstance(arg_value, discord.TextChannel)
                or isinstance(arg_value, discord.Role)
            ):
                embed.add_field(name=arg_name, value=arg_value.mention)
            else:
                embed.add_field(name=arg_name, value=str(arg_value))

        if channel:
            await channel.send(embed=embed)


class PunishmentManager:
    def __init__(self):
        self.bot = None
        self.database = None
        self.infractions_table = None

    async def setup(self, bot):
        """Setup the punishment manager."""
        self.bot = bot
        self.database = self.bot.database

        self.infractions = await self.database.new_table(
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

    async def start_tracking(self):
        """Start tracking any incomplete punishments."""
        records = await self.infractions.filter(
            where=DBFilter(expiry_date__ne=None, completed=False)
        )
        for record in records:
            guild = self.bot.get_guild(int(record["guild_id"]))
            user = discord.Object(id=int(record["member_id"]))
            delay.start_waiting(
                date=record["expiry_date"],
                callback=self.end_punishment,
                args=(record["type"], record["id"], guild, user)
            )
    
    async def add_punishment(self, punishment_type, *, author, member, expiry_date=None):
        """Add a punishment to the database and start tracking it."""
        punishment_id = await self.infractions.new_record_with_id(
            guild_id=member.guild.id,
            member_id=member.id,
            author_id=author.id,
            type=punishment_type,
            issue_date=datetime.now(),
            expiry_date=expiry_date,
        )

        if expiry_date:
            user = discord.Object(id=member.id)
            guild = member.guild
            delay.start_waiting(
                date=expiry_date,
                callback=self.end_punishment,
                args=(punishment_type, punishment_id, guild, user)
            )

    async def end_punishment(self, punishment_type, punishment_id, guild, user):
        """End a punishment and execute any post-punishment callbacks."""
        await self.infractions.update_records(where=DBFilter(id=punishment_id), completed=True)
        if punishment_type == "ban":
            await guild.unban(user)
        elif punishment_type == "mute":
            mute_role = await db.extras.get_role(self.bot.database, guild, "mute_role")
            member = guild.get_member(user.id)
            await member.remove_roles(mute_role)