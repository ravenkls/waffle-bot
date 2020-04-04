

async def get_role(database, guild, name):
    role = await database.get_setting(guild, name)
    if role:
        return guild.get_role(int(role))

async def set_role(database, guild, name, role):
    await database.set_setting(guild, name, role.id)

async def get_admin_role(ctx):
    return await get_role(ctx.bot.database, ctx.guild, "admin_role")

async def set_admin_role(ctx, role):
    await set_role(ctx.bot.database, ctx.guild, "admin_role", role)

async def get_mod_role(ctx):
    return await get_role(ctx.bot.database, ctx.guild, "mod_role")

async def set_mod_role(ctx, role):
    await set_role(ctx.bot.database, ctx.guild, "mod_role", role)

async def get_mute_role(ctx):
    return await get_role(ctx.bot.database, ctx.guild, "mute_role")

async def set_mute_role(ctx, role):
    await set_role(ctx.bot.database, ctx.guild, "mute_role", role)