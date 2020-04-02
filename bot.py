from discord.ext import commands

with open("token.txt") as f:
    token = f.read()

bot = commands.Bot(command_prefix="?")
bot.load_extension("general")
bot.run(token)