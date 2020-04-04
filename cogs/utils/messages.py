import discord
from discord.ext import commands
import datetime
import re


async def send_embed(dest, message):
    embed = discord.Embed(description=message)
    return await dest.send(embed=embed)



class Duration(commands.Converter):

    async def convert(self, ctx, argument):
        """Converts a string like 1w2d into a datetime."""
        string = str(argument)
        times = [0, 0, 0, 0, 0, 0]
        matches = re.findall(r"(?:(\d+)y)?(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", string)
        
        if matches:
            for n, time_length in enumerate(matches[0]):
                if time_length:
                    times[n] += int(time_length)
        
        timedelta = datetime.timedelta( 
            weeks=times[1], 
            days=times[2] + times[0],
            hours=times[3], 
            minutes=times[4], 
            seconds=times[5]
        )

        if timedelta.total_seconds() > 0:
            return timedelta
        else:
            raise commands.errors.BadArgument("The duration must be entered in the correct format (e.g. 1w2d)")