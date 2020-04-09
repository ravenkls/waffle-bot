import discord
from discord.ext import commands
from .exceptions import CantModifyError, BotHasLowRankError
from . import db


async def is_admin(ctx):
    """Checks whether the author is an Administrator."""
    if ctx.author == ctx.guild.owner:
        return True

    admin_role = await db.extras.get_admin_role(ctx)
    if admin_role:
        if ctx.author.top_role >= admin_role:
            return True
        else:
            await ctx.send("You are not an Administrator.")


async def is_moderator(ctx):
    """Checks whether the author is a Moderator."""
    if ctx.author == ctx.guild.owner:
        return True

    mod_role = await db.extras.get_mod_role(ctx)
    if mod_role:
        if ctx.author.top_role >= mod_role:
            return True
        else:
            await ctx.send("You are not a Moderator.")


def can_modify_member(ctx, member):
    """Checks whether the author has permission to
    modify (i.e. kick, ban, mute, warn) another member.

    If these checks fail, an error is raised."""
    if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
        raise CantModifyError()
    elif ctx.me.top_role <= member.top_role:
        raise BotHasLowRankError()


def can_modify_role(ctx, role):
    """Checks whether the author has permission to
    modify (e.g. delete members from a role) another role.

    If these checks fail, an error is raised."""
    if ctx.author.top_role <= role and ctx.author != ctx.guild.owner:
        raise CantModifyError()
    elif ctx.me.top_role <= role:
        raise BotHasLowRankError()


def member_is_other(ctx, member):
    """Checks whether the target member is another
    member of the server.

    If this check fails, an error is raised."""
    if ctx.author == member:
        raise commands.errors.CommandError("You cannot use this command on yourself.")
    elif member.bot:
        raise commands.errors.CommandError("You cannot use this command on a bot.")


async def is_guild_owner(ctx):
    if ctx.author == ctx.guild.owner:
        return True
    else:
        await ctx.send("Only the server owner can run this command.")