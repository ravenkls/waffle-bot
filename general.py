import inspect
import discord
from discord.ext import commands
import datetime
import humanize


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")
        self.start_time = datetime.datetime.now()

    def get_usage(self, command):
        """Gets the usage of a command."""
        argspec = inspect.getfullargspec(command.callback)

        required_arguments = []
        optional_arguments = []
        kwonly_arguments = []

        if argspec.defaults:
            defaults_index = len(argspec.args) - len(argspec.defaults)
            positional_arguments = argspec.args[2:defaults_index]
            kw_arguments = argspec.args[defaults_index:]

            for arg, default in zip(kw_arguments, argspec.defaults):
                if default is not None:
                    optional_arguments.append(f"[{arg}={default}]")
                else:
                    optional_arguments.append(f"[{arg}]")
        else:
            positional_arguments = argspec.args[2:]

        for arg in positional_arguments:
            required_arguments.append(f"<{arg}>")

        for arg in argspec.kwonlyargs:
            if arg in argspec.kwonlydefaults:
                default = argspec.kwonlydefaults[arg]
                if default is not None:
                    optional_arguments.append(f"[{arg}={default}]")
                else:
                    optional_arguments.append(f"[{arg}]")
            else:
                kwonly_arguments.append(f"<{arg}>")

        arguments = required_arguments + optional_arguments + kwonly_arguments

        return f"{self.bot.command_prefix}{command.name} " + " ".join(arguments)

    @commands.command()
    async def help(self, ctx, command=None):
        """Displays a list of bot commands."""
        if command is None:
            embed = discord.Embed(title="Commands are listed below", 
                                  description=f"Type `{self.bot.command_prefix}help <command>`"
                                               " more details on a command.")

            for name, cog in self.bot.cogs.items():
                cog_commands = [c for c in cog.get_commands() if not c.hidden]
                commands_list = ", ".join([f"`{self.bot.command_prefix}{cc.name}`" for cc in cog_commands])
                embed.add_field(name=name, value=commands_list, inline=False)

        elif command := self.bot.get_command(command):
            embed = discord.Embed(title=command.name, description=command.callback.__doc__)
            embed.add_field(name="Usage", value=f"`{self.get_usage(command)}`")

        embed.set_author(name=self.bot.user.name, 
                         icon_url=self.bot.user.avatar_url_as(format="png", static_format="png"))

        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """Displays how long I've been online for."""
        uptime = datetime.datetime.now() - self.start_time
        uptime_string = humanize.naturaldelta(uptime)
        embed = discord.Embed(description=f"I have been online for {uptime_string}")
        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member):
        """Displays information about a user."""
        now = datetime.datetime.now()

        join_date = humanize.naturalday(member.joined_at)
        join_ago = (now - member.joined_at).days

        creation_date = humanize.naturalday(member.created_at)
        creation_ago = (now - member.joined_at).days

        embed = discord.Embed(title="User Details", description=member.mention)
        embed.set_author(name=member.name, icon_url=member.avatar_url_as(format="png", static_format="png"))
        embed.set_footer(text=str(member.id))
        embed.set_thumbnail(url=member.avatar_url_as(format="png", static_format="png"))

        embed.add_field(name="Guild Join Date", value=f"{join_date} ({join_ago} days ago)")
        embed.add_field(name="Account Creation Date", value=f"{creation_date} ({creation_ago} days ago)")
        embed.add_field(name="Roles", value=" ".join([r.mention for r in member.roles[1:]]), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Pong!"""
        response = await ctx.send("ping...")
        difference = (response.created_at - ctx.message.created_at)
        latency = int(difference.total_seconds() * 1000)
        await response.edit(content=f"Pong! `{latency}ms`")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, exception):
        if isinstance(exception, discord.ext.commands.errors.CommandNotFound):
            return
        elif isinstance(exception, discord.ext.commands.errors.CheckFailure):
            return
        elif isinstance(exception, discord.ext.commands.errors.NoPrivateMessage):
            message = "This command can only be used in servers"
        elif isinstance(exception, discord.ext.commands.errors.MissingRequiredArgument):
            message = f"{exception.param.name} is a required argument"
        elif isinstance(exception, discord.ext.commands.errors.BadArgument):
            message = exception.message
        elif type(exception) == discord.ext.commands.CommandInvokeError:
            if type(exception.original) == discord.errors.Forbidden:
                message = "I don't have permission to carry out that action"

        embed = discord.Embed(description=message, colour=0xc42929)
        embed.add_field(name="Usage", value=f"`{self.get_usage(ctx.command)}`")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))