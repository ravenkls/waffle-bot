import discord


async def send_embed(dest, message):
    embed = discord.Embed(description=message)
    return await dest.send(embed=embed)
