import asyncio
import datetime
import typing

import discord
from discord.ext import commands
import humanize

from .utils import checks, db
from .utils.db.database import DBFilter
from .utils.db.fields import *
from .utils.controllers import ChannelLogger, PunishmentManager, ReactionRoleManager
from .utils.messages import MessageBox, Duration, NegativeBoolean, EveryoneRole


modlogger = ChannelLogger("moderation_log")
punishments = PunishmentManager()
reaction_roles = ReactionRoleManager()


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🔨"
        
        loop = asyncio.get_event_loop()
        loop.create_task(self.setup())
        
    async def setup(self):
        await self.bot.wait_until_ready()
        await punishments.setup(self.bot)
        await reaction_roles.setup(self.bot)

        await punishments.start_tracking()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.bot.wait_until_ready()
        mute_role = await db.extras.get_role(self.bot.database, channel.guild, "mute_role")
        if mute_role:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.bot.wait_until_ready()
        punishment = await punishments.get_punishment("mute", member.guild, member)
        if punishment:
            mute_role = await db.extras.get_role(self.bot.database, member.guild, "mute_role")
            if mute_role:
                await member.add_roles(mute_role)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.bot.wait_until_ready()
        await reaction_roles.check_reaction_add(payload)

    async def cog_check(self, ctx):
        return await checks.is_admin(ctx)

    @commands.guild_only()
    @commands.command()
    async def modlog(self, ctx, channel: typing.Union[discord.TextChannel, NegativeBoolean] = None):
        """Set the channel to send mod logs to."""
        if channel is None:
            channel = await modlogger.get_channel(ctx)
            if channel is None:
                await ctx.send(embed=MessageBox.warning("You have not set a moderation log channel yet on this server!"))
            else:
                await ctx.send(embed=MessageBox.info(f"{channel.mention} is the moderation log channel."))
        elif isinstance(channel, discord.TextChannel):
            await modlogger.set_channel(ctx, channel)
            await ctx.send(embed=MessageBox.confirmed(f"{channel.mention} is now the moderation log."))
        elif channel is False:
            await modlogger.set_channel(ctx, None)
            await ctx.send(embed=MessageBox.confirmed("The moderation log channel has been reset"))

    @commands.guild_only()
    @commands.check(checks.is_guild_owner)
    @commands.command()
    async def adminrole(self, ctx, role: typing.Union[discord.Role, NegativeBoolean] = None):
        """Display or set the Administrator role."""
        if role is None:
            admin_role = await db.extras.get_admin_role(ctx)
            if admin_role:
                await ctx.send(embed=MessageBox.info(f"{admin_role.mention} is the Administrator role."))
            else:
                await ctx.send(embed=MessageBox.warning("You have not set an Administrator role."))
        elif isinstance(role, discord.Role):
            await db.extras.set_admin_role(ctx, role)
            await ctx.send(embed=MessageBox.confirmed(f"{role.mention} is now the Administrator role."))
        elif role is False:
            await db.extras.set_admin_role(ctx, None)
            await ctx.send(embed=MessageBox.confirmed("The Administrator role has been reset."))

    @commands.guild_only()
    @commands.command()
    async def modrole(self, ctx, role: typing.Union[discord.Role, NegativeBoolean] = None):
        """Display or set the Moderator role."""
        if role is None:
            mod_role = await db.extras.get_mod_role(ctx)
            if mod_role:
                await ctx.send(embed=MessageBox.info(f"{mod_role.mention} is the Moderator role."))
            else:
                await ctx.send(embed=MessageBox.warning(f"You have not set an Moderator role."))
        elif isinstance(role, discord.Role):
            await db.extras.set_mod_role(ctx, role)
            await ctx.send(embed=MessageBox.confirmed(f"{role.mention} is now the Moderator role."))
        elif role is False:
            await db.extras.set_mod_role(ctx, None)
            await ctx.send(embed=MessageBox.confirmed("The Moderation role has been reset."))

    @commands.guild_only()
    @commands.command()
    async def muterole(self, ctx, role: typing.Union[discord.Role, NegativeBoolean] = None):
        """Display or set the Mute role."""
        if role is None:
            mute_role = await db.extras.get_role(self.bot.database, ctx.guild, "mute_role")
            if mute_role:
                await ctx.send(embed=MessageBox.info(f"{mute_role.mention} is the Mute role."))
            else:
                await ctx.send(embed=MessageBox.warning(f"You have not set an Mute role."))
        elif isinstance(role, discord.Role):
            await db.extras.set_role(self.bot.database, ctx.guild, "mute_role", role)
            await ctx.send(embed=MessageBox.confirmed(f"{role.mention} is now the Mute role."))

            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
        elif role is False:
            mute_role = await db.extras.get_role(self.bot.database, ctx.guild, "mute_role")
            message = await ctx.send(embed=MessageBox.loading("Cleaning up Mute role permissions."))
            if mute_role:
                for channel in ctx.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=None, speak=None, add_reactions=False)
            await db.extras.set_role(self.bot.database, ctx.guild, "mute_role", None)
            await message.edit(embed=MessageBox.confirmed("The Mute role has been reset."))

    @commands.guild_only()
    @commands.command()
    async def roles(self, ctx, action, current_role: typing.Union[discord.Role, EveryoneRole], roles: commands.Greedy[discord.Role]):
        """Manage server roles.

        Examples:
        `roles add Moderator Admin` Gives everyone with the Moderator role the Admin role
        `roles remove everyone Moderator` Removes the Moderator role from everyone
        `roles switch Moderator Admin` Moves all Moderators to the Admin role"""
        checks.can_modify_role(ctx, current_role)
        [checks.can_modify_role(ctx, r) for r in roles]
        role_mentions = " and ".join([r.name for r in roles])
        if action.lower() == "add":
            message = await ctx.send(embed=MessageBox.loading(f"Adding {role_mentions} to members with the {current_role} role."))
            for m in current_role.members:
                await m.add_roles(*roles)
        elif action.lower() == "remove":
            message = await ctx.send(embed=MessageBox.loading(f"Removing {role_mentions} from members with the {current_role} role."))
            for m in current_role.members:
                await m.remove_roles(*roles)
        elif action.lower() == "switch":
            message = await ctx.send(embed=MessageBox.loading(f"Adding {role_mentions} from members with the {current_role} role and removing their {current_role} role."))
            for m in current_role.members:
                await m.add_roles(*roles)
                await m.remove_roles(current_role)
        else:
            raise commands.errors.BadArgument('The "action" parameter must be one of `add`, `remove`, or `switch`.')
        await message.edit(embed=MessageBox.success("Roles have been changed successfully."))

    @commands.guild_only()
    @commands.command(aliases=["rradd"])
    async def addreactionrole(self, ctx, message_id: int, role: discord.Role, emoji, nick: str = None):
        """Enter reaction role setup."""
        message = await ctx.channel.fetch_message(message_id)
        await reaction_roles.add_reaction_role(message, emoji, role, nick)
        await ctx.message.delete()
        msg = await ctx.send(embed=MessageBox.success(f"{role} has been added to [this message]({message.jump_url})"))
        await asyncio.sleep(5)
        await msg.delete()

    @commands.guild_only()
    @commands.command(aliases=["rrdel"])
    async def delreactionrole(self, ctx, message_id: int, emoji):
        """Enter reaction role setup."""
        message = await ctx.channel.fetch_message(message_id)
        await reaction_roles.remove_reaction_role(message, emoji)
        await ctx.message.delete()
        msg = await ctx.send(embed=MessageBox.success(f"{str(emoji)} has been removed from [this message]({message.jump_url})"))
        await asyncio.sleep(5)
        await msg.delete()

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def ban(self, ctx, member: typing.Union[discord.Member, int], duration: typing.Optional[Duration], *, reason=None):
        """Ban a member of the server.

        Examples:
        `ban Kristian` Bans the user 'Kristian' indefinitely
        `ban Kristian 5w2d10m` Bans the user 'Kristian' for 5 weeks, 2 days and 10 minutes
        `ban Kristian 2d Posting NSFW` Bans the user 'Kristian' for 2 days for 'Posting NSFW'
        `ban 144912469071101952` Bans the user with ID 144912469071101952 indefinitely"""
        if isinstance(member, discord.Member):
            checks.can_modify_member(ctx, member)
            await member.send(embed=MessageBox.critical(f"You have been banned from {ctx.guild.name}. Reason: {reason}"))
        else:
            member = discord.Object(id=member)

        try:
            await ctx.guild.ban(member, reason=reason)
        except discord.errors.NotFound:
            raise commands.errors.BadArgument(f'User "{member.id}" not found')

        member_name = member.mention if isinstance(member, discord.Member) else f"User with ID {member.id}"
        await ctx.send(embed=MessageBox.success(f"{member_name} has been banned. Reason {reason}"))

        expiry_date = datetime.datetime.now() + duration if duration else None
        await punishments.add_punishment(
            "ban",
            author=ctx.author,
            user=member,
            reason=str(reason),
            expiry_date=expiry_date
        )

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def unban(self, ctx, user: discord.User, reason=None):
        """Unban a user from the server."""
        try:
            await ctx.guild.unban(user)
        except discord.errors.NotFound:
            raise commands.errors.CommandError("That user is not banned.")

        await ctx.send(embed=MessageBox.success(f"{user.mention} has been unbanned. Reason: {reason}"))
        punishment = await punishments.get_punishment("ban", ctx.guild, user)
        if punishment:
            await punishments.complete_punishment(punishment["id"])

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        checks.can_modify_member(ctx, member)
        await member.send(f"👢 You have been kicked from {ctx.guild.name}. Reason: {reason}")
        await member.kick(reason=reason)
        await ctx.send(embed=MessageBox.success(f"{member.mention} has been kicked. Reason: {reason}"))
        await punishments.add_punishment("kick", author=ctx.author, user=member, reason=str(reason))

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def lock(self, ctx):
        """Locks the channel, prevents anyone from sending messages in the channel.
        Note: this only works if the server permissions have been setup correctly."""
        if ctx.channel.overwrites_for(ctx.guild.default_role).send_messages != False:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
            await ctx.send(embed=MessageBox.success("This channel has now been locked."))
        else:
            raise commands.errors.CommandError("This channel is already locked.")

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def unlock(self, ctx):
        """Unlocks the channel (i.e. undos the `lock` command)."""
        if ctx.channel.overwrites_for(ctx.guild.default_role).send_messages is False:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
            await ctx.send(embed=MessageBox.success("This channel has now been unlocked."))
        else:
            raise commands.errors.CommandError("This channel is already unlocked.")

    @commands.guild_only()
    @commands.command(aliases=["purge", "clear", "cls"])
    async def clean(self, ctx, amount=10):
        await ctx.message.delete()
        messages = await ctx.channel.purge(limit=amount)
        tmp = await ctx.send(embed=MessageBox.success(f"{len(messages)} messages were deleted."))
        await asyncio.sleep(5)

        try:
            await tmp.delete()
        except discord.errors.NotFound:
            pass


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🚔"

    async def cog_check(self, ctx):
        return await checks.is_moderator(ctx)

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        """Warn a member of the server."""
        checks.can_modify_member(ctx, member)
        await punishments.add_punishment("warn", author=ctx.author, user=member, reason=str(reason))
        await member.send(embed=MessageBox.warning(f"You have been warned on {ctx.guild.name}. Reason: {reason}"))
        await ctx.send(embed=MessageBox.success(f"{member.mention} has been warned. Reason: {reason}"))

    @commands.guild_only()
    @commands.command(aliases=["warns", "warnings"])
    async def infractions(self, ctx, member: discord.Member, page: int = 1):
        """View all the infractions that a member has been given."""
        infractions = await punishments.infractions.filter(
            where=DBFilter(guild_id=ctx.guild.id, member_id=member.id, type="warn")
        )
        if not infractions:
            return await ctx.send(embed=MessageBox.info(f"{member.mention} has no previous infractions."))

        pages = (len(infractions) - 1) // 20 + 1
        page = max(min(pages, page), 1)

        last_24_hours = 0
        last_14_days = 0
        last_90_days = 0
        infraction_descriptions = []

        for n, infraction in enumerate(sorted(infractions, key=lambda r: r["issue_date"], reverse=True)):
            if infraction["issue_date"] >= datetime.datetime.now() - datetime.timedelta(days=1):
                last_24_hours += 1
            if infraction["issue_date"] >= datetime.datetime.now() - datetime.timedelta(days=14):
                last_14_days += 1
            if infraction["issue_date"] >= datetime.datetime.now() - datetime.timedelta(days=90):
                last_90_days += 1
            if (page-1)*20 <= n and len(infraction_descriptions) < 20:
                ts = humanize.naturaldelta(datetime.datetime.now() - infraction["issue_date"])
                infraction_descriptions.append(f"**[`{infraction['id']}`] {ts} ago** • {infraction['reason']}")

        embed = discord.Embed(description=f"{member.mention} has `{len(infractions)}` infractions in total.")
        embed.set_author(
            name=f"{member}'s infractions",
            icon_url=member.avatar_url_as(format="png", static_format="png")
        )
        embed.add_field(name="Last 24 Hours", value=f"{last_24_hours} infractions")
        embed.add_field(name="Last 14 Days", value=f"{last_14_days} infractions")
        embed.add_field(name="Last 3 Months", value=f"{last_90_days} infractions")
        embed.add_field(name="All Infractions", value="\n".join(infraction_descriptions))
        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(aliases=["warning"])
    async def infraction(self, ctx, id: int):
        """Get details on a particular infraction."""
        infractions = await punishments.infractions.filter(
            where=DBFilter(guild_id=ctx.guild.id, id=id)
        )
        if not infractions:
            raise commands.errors.CommandError(f"There is no infraction with the ID {id}.")
        infraction = infractions[0]
        member = ctx.guild.get_member(int(infraction["member_id"]))
        author = ctx.guild.get_member(int(infraction["author_id"]))

        embed = discord.Embed(title=f"Infraction {id}: Details")
        embed.set_author(
            name=str(member),
            icon_url=member.avatar_url_as(format="png", static_format="png")
        )
        embed.set_thumbnail(url=member.avatar_url_as(format="png", static_format="png"))
        embed.add_field(name="Given to", value=member.mention)
        embed.add_field(name="Given by", value=author.mention)
        embed.add_field(name="Reason", value=infraction["reason"])
        embed.add_field(name="Issue Date", value=infraction["issue_date"])
        if expiry_date := infraction["expiry_date"]:
            embed.add_field(name="Expiry Date", value=expiry_date)

        await ctx.send(embed=embed)

    @modlogger.log_action
    @commands.guild_only()
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
        await punishments.add_punishment(
            "mute",
            author=ctx.author,
            user=member,
            reason=str(reason),
            expiry_date=expiry_date
        )
        await ctx.send(embed=MessageBox.success(f"{member.mention} has been muted. Reason: {reason}"))

    @modlogger.log_action
    @commands.guild_only()
    @commands.command()
    async def unmute(self, ctx, member: discord.Member, reason=None):
        """Unmute a member of the server."""
        checks.can_modify_member(ctx, member)
        mute_role = await db.extras.get_role(self.bot.database, ctx.guild, "mute_role")
        await member.remove_roles(mute_role)

        await ctx.send(embed=MessageBox.success(f"{member.mention} has been unmuted. Reason: {reason}"))
        punishment = await punishments.get_punishment("mute", ctx.guild, member)
        if punishment:
            await punishments.complete_punishment(punishment["id"])


def setup(bot):
    bot.add_cog(Admin(bot))
    bot.add_cog(Moderation(bot))
