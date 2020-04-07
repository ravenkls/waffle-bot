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
        """Decorator for registering a command that should be logged."""
        command.after_invoke(self.send_command_log)
        return command

    async def set_channel(self, ctx, channel):
        """Set the logging channel."""
        if channel is not None:
            await ctx.bot.database.set_setting(ctx.guild, self.name, channel.id)
        else:
            await ctx.bot.database.set_setting(ctx.guild, self.name, None)

    async def get_channel(self, ctx):
        """Get the logging channel."""
        channel_id = await ctx.bot.database.get_setting(ctx.guild, self.name)
        if channel_id:
            return ctx.guild.get_channel(int(channel_id))

    async def send_command_log(self, cog, ctx):
        """Send a command log to the log channel."""
        if ctx.command_failed:
            return

        channel = await self.get_channel(ctx)
        embed = discord.Embed(
            title=ctx.bot.command_prefix + ctx.command.name,
            description=f"[Jump to message]({ctx.message.jump_url})",
            timestamp=datetime.now(),
        )
        embed.set_author(
            name=str(ctx.author),
            icon_url=ctx.author.avatar_url_as(format="png", static_format="png")
        )

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
        self.infractions = None

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
                Text("reason"),
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

    async def add_punishment(self, punishment_type, *, author, user, reason, expiry_date=None):
        """Add a punishment to the database and start tracking it."""
        punishment_id = await self.infractions.new_record_with_id(
            guild_id=author.guild.id,
            member_id=user.id,
            author_id=author.id,
            type=punishment_type,
            reason=reason,
            issue_date=datetime.now(),
            expiry_date=expiry_date,
        )

        if expiry_date:
            user = discord.Object(id=user.id)
            guild = author.guild
            delay.start_waiting(
                date=expiry_date,
                callback=self.end_punishment,
                args=(punishment_type, punishment_id, guild, user)
            )

    async def get_punishment(self, punishment_type, guild, user):
        """Get a punishment and return the details."""
        records = await self.infractions.filter(
            where=DBFilter(
                type=punishment_type,
                guild_id=guild.id,
                member_id=user.id,
                completed=False,
                expiry_date=None,
                expiry_date__gt=datetime.now(),
            )
        )
        if records:
            return records[0]

    async def complete_punishment(self, punishment_id):
        await self.infractions.update_records(where=DBFilter(id=punishment_id), completed=True)

    async def end_punishment(self, punishment_type, punishment_id, guild, user):
        """End a punishment and execute any post-punishment callbacks."""
        await self.complete_punishment(punishment_id)
        if punishment_type == "ban":
            await guild.unban(user)
        elif punishment_type == "mute":
            mute_role = await db.extras.get_role(self.bot.database, guild, "mute_role")
            member = guild.get_member(user.id)
            await member.remove_roles(mute_role)


class ReactionRoleManager:
    def __init__(self):
        self.bot = None
        self.database = None
        self.reaction_roles = None

    async def setup(self, bot):
        """Setup the punishment manager."""
        self.bot = bot
        self.database = self.bot.database

        self.reaction_roles = await self.database.new_table(
            "reaction_roles",
            (
                BigInteger("guild_id"),
                BigInteger("channel_id"),
                BigInteger("message_id"),
                Text("emoji"),
                BigInteger("role_id"),
                Text("nickname"),
            ),
        )
    
    async def add_reaction_role(self, message, emoji, role, nick=None):
        """Add a role reaction to a message."""
        await self.reaction_roles.new_record(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            emoji=str(emoji),
            role_id=role.id,
            nickname=nick,
        )
        await message.add_reaction(emoji)

    async def remove_reaction_role(self, message, emoji):
        """Remove a role reaction from a message."""
        await self.reaction_roles.delete_records(
            where=DBFilter(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                message_id=message.id,
                emoji=str(emoji),
            )
        )
        await message.remove_reaction(emoji, message.guild.get_member(self.bot.user.id))

    async def get_reaction_roles(self, message):
        """Get all reaction roles for a message."""
        return await self.reaction_roles.filter(
            where=DBFilter(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                message_id=message.id,
            )
        )

    async def check_reaction_add(self, payload):
        """Check whether to add roles to a member when
        they react to a message."""
        if payload.member.bot:
            return

        records = await self.reaction_roles.filter(
            where=DBFilter(
                guild_id=payload.guild_id,
                channel_id=payload.channel_id,
                message_id=payload.message_id,
                emoji=str(payload.emoji)
            )
        )

        if not records:
            return

        guild = self.bot.get_guild(payload.guild_id)
        roles = [guild.get_role(r["role_id"]) for r in records]
        nickname = [r["nickname"] for r in records if r["nickname"]]
        if nickname:
            nickname = nickname[0]

        if all(r in payload.member.roles for r in roles):
            await payload.member.remove_roles(*roles)
            if nickname:
                new_nick = payload.member.display_name.split("||")[0].strip()
                try:
                    await payload.member.edit(nick=new_nick)
                except discord.errors.Forbidden:
                    pass
        else:
            await payload.member.add_roles(*roles)
            if nickname:
                nick_length = len(" || " + nickname)
                max_len = 32 - nick_length
                new_nick = payload.member.display_name[:max_len] + " || " + nickname
                try:
                    await payload.member.edit(nick=new_nick)
                except discord.errors.Forbidden:
                    pass

        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji, payload.member)