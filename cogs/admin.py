import asyncio
import datetime
import typing

import discord
from discord.ext import commands

from .utils import checks, db
from .utils.db.database import DBFilter
from .utils.db.fields import *
from .utils.controllers import ChannelLogger, PunishmentManager
from .utils.messages import MessageBox, Duration


modlogger = ChannelLogger("moderation_log")
punishments = PunishmentManager()


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🔨"

    @commands.Cog.listener()
    async def on_ready(self):
        await punishments.setup(self.bot)
        await punishments.start_tracking()
    
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
                await ctx.send(embed=MessageBox.warning("You have not set a moderation log channel yet on this server!"))
            else:
                await ctx.send(embed=MessageBox.info(f"{channel.mention} is the moderation log channel."))
        else:
            await modlogger.set_channel(ctx, channel)
            await ctx.send(embed=MessageBox.confirmed(f"{channel.mention} is now the moderation log."))

    @commands.command()
    @commands.is_owner()
    async def adminrole(self, ctx, role: discord.Role = None):
        """Display or set the Administrator role."""
        if role is None:
            admin_role = await db.extras.get_admin_role(ctx)
            if admin_role:
                await ctx.send(embed=MessageBox.info(f"{admin_role.mention} is the Administrator role."))
            else:
                await ctx.send(embed=MessageBox.warning("You have not set an Administrator role."))
        else: 
            await db.extras.set_admin_role(ctx, role)
            await ctx.send(embed=MessageBox.confirmed(f"{role.mention} is now the Administrator role."))

    @commands.command()
    async def modrole(self, ctx, role: discord.Role = None):
        """Display or set the Moderator role."""
        if role is None:
            mod_role = await db.extras.get_mod_role(ctx)
            if mod_role:
                await ctx.send(embed=MessageBox.info(f"{mod_role.mention} is the Moderator role."))
            else:
                await ctx.send(embed=MessageBox.warning(f"You have not set an Moderator role."))
        else:
            await db.extras.set_mod_role(ctx, role)
            await ctx.send(embed=MessageBox.confirmed(f"{role.mention} is now the Moderator role."))

    @commands.command()
    async def muterole(self, ctx, role: discord.Role = None):
        """Display or set the Mute role."""
        if role is None:
            mute_role = await db.extras.get_role(self.bot.database, ctx.guild, "mute_role")
            if mute_role:
                await ctx.send(embed=MessageBox.info(f"{mute_role.mention} is the Mute role."))
            else:
                await ctx.send(embed=MessageBox.warning(f"You have not set an Mute role."))
        else:
            await db.extras.set_role(self.bot.database, ctx.guild, "mute_role", role)
            await ctx.send(embed=MessageBox.confirmed(f"{role.mention} is now the Mute role."))

            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)


    @modlogger.log_action
    @commands.command()
    async def ban(self, ctx, member: discord.Member, duration: typing.Optional[Duration], *, reason=None):
        """Ban a member of the server.
        
        Examples:
        `ban Kristian` Bans the user 'Kristian' indefinitely
        `ban Kristian 5w2d10m` Bans the user 'Kristian' for 5 weeks, 2 days and 10 minutes
        `ban Kristian 2d Posting NSFW` Bans the user 'Kristian' for 2 days for 'Posting NSFW'"""
        checks.can_modify_member(ctx, member)

        await member.send(f"🔨 You have been banned from {ctx.guild.name}. Reason: {reason}")
        await member.ban(reason=reason)
        await ctx.send(embed=MessageBox.confirmed(f"{member.mention} has been banned. Reason: {reason}"))
        
        expiry_date = datetime.datetime.now() + duration if duration else None
        await punishments.add_punishment("ban", author=ctx.author, member=member, expiry_date=expiry_date)

    @modlogger.log_action
    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        checks.can_modify_member(ctx, member)
        await member.send(f"👢 You have been kicked from {ctx.guild.name}. Reason: {reason}")
        await member.kick(reason=reason)
        await ctx.send(embed=MessageBox.confirmed(f"{member.mention} has been kicked. Reason: {reason}"))
        await punishments.add_punishment("kick", author=ctx.author, member=member)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🚔"

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
        await punishments.add_punishment("warn", author=ctx.author, member=member)
        await ctx.send(embed=MessageBox.confirmed(f"{member.mention} has been warned. Reason: {reason}"))

    @modlogger.log_action
    @commands.command()
    async def mute(self, ctx, member: discord.Member, duration: typing.Optional[Duration], *, reason=None):
        """Mute a member of the server.
        
        Examples:
        `mute Kristian` Mutes the user 'Kristian' indefinitely
        `mute Kristian 5w2d10m` Mutes the user 'Kristian' for 5 weeks, 2 days and 10 minutes
        `mute Kristian 2d Posting NSFW` Mutes the user 'Kristian' for 2 days for 'Posting NSFW'"""
        checks.can_modify_member(ctx, member)
        mute_role = await db.extras.get_role(self.bot.database, ctx.guild, "mute_role")
        await member.add_roles(mute_role)

        expiry_date = datetime.datetime.now() + duration if duration else None
        await punishments.add_punishment("mute", author=ctx.author, member=member, expiry_date=expiry_date)
        await ctx.send(embed=MessageBox.confirmed(f"{member.mention} has been muted. Reason: {reason}"))

def setup(bot):
    bot.add_cog(Admin(bot))
    bot.add_cog(Moderation(bot))
