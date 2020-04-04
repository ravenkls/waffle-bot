import discord
import inspect
from datetime import datetime


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
