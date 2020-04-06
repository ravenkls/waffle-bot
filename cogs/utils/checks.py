import discord
from discord.ext import commands
from .exceptions import CantModifyError, BotHasLowRankError


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


def author_is_not_member(ctx, member):
    """Checks whether the command author is not the
    member.

    If this check fails, an error is raised."""
    if ctx.author == member:
        raise commands.errors.CommandError("You cannot use this command on yourself.")


async def is_guild_owner(ctx):
    if ctx.author == ctx.guild.owner:
        return True
    else:
        await ctx.send("Only the server owner can run this command.")