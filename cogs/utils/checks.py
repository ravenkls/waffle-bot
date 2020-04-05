import discord
from discord.ext import commands
from .exceptions import ModifyMemberError, BotHasLowRankError


def can_modify_member(ctx, member):
    """Checks whether the author has permission to
    modify (i.e. kick, ban, mute, warn) another member.

    If these checks fail, an error is raised."""
    if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
        raise ModifyMemberError()
    elif ctx.me.top_role <= member.top_role:
        raise BotHasLowRankError()
