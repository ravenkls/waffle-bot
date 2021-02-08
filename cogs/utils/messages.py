import discord
from discord.ext import commands
import datetime
import re


class MessageBox(discord.Embed):
    @classmethod
    def info(cls, message):
        return cls(colour=0x3B88C3, description=message)

    @classmethod
    def confirmed(cls, message):
        return cls(colour=0x226699, description=f"☑️    {message}")

    @classmethod
    def success(cls, message):
        return cls(colour=0x77B255, description=f"✅    {message}")

    @classmethod
    def warning(cls, message):
        return cls(colour=0xFFCC4D, description=f"⚠️    {message}")

    @classmethod
    def critical(cls, message):
        embed = cls(colour=0xBE1931)
        embed.set_author(name=message, icon_url="https://i.imgur.com/OjJaekp.png")
        return embed

    @classmethod
    def loading(cls, message):
        embed = cls(colour=0xFEAC33)
        embed.set_author(name=message, icon_url="https://i.imgur.com/z6imAKZ.gif")
        return embed


class Duration(commands.Converter):
    async def convert(self, ctx, argument):
        """Converts a string like 1w2d into a datetime."""
        string = str(argument)
        times = [0, 0, 0, 0, 0, 0]
        matches = re.findall(
            r"(?:(\d+)y)?(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?",
            string,
        )

        if matches:
            for n, time_length in enumerate(matches[0]):
                if time_length:
                    times[n] += int(time_length)

        timedelta = datetime.timedelta(
            weeks=times[1],
            days=times[2] + times[0] * 365,
            hours=times[3],
            minutes=times[4],
            seconds=times[5],
        )

        if timedelta.total_seconds() > 0:
            return timedelta
        raise commands.errors.BadArgument(
            "The duration must be entered in the correct format (e.g. 1w2d)"
        )


class NegativeBoolean(commands.Converter):
    async def convert(self, ctx, argument):
        """Converts a negative argument into a False boolean."""
        if str(argument).lower() in ("off", "disable", "false"):
            return False
        raise commands.errors.BadArgument(
            "A negative boolean should either be `off`, `disable` or `false`."
        )


class EveryoneRole(commands.Converter):
    async def convert(self, ctx, argument):
        """Converts an argument into the everyone role."""
        if argument == "everyone":
            return ctx.guild.default_role
        raise commands.errors.BadArgument(
            "Specify the everyone role by typing the word `everyone`"
        )
