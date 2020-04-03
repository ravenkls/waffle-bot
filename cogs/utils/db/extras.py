

async def get_admin_role(ctx):
    admin_id = await ctx.bot.database.get_setting(ctx.guild, "admin_role")
    if admin_id:
        return ctx.guild.get_role(int(admin_id))


async def set_admin_role(ctx, role):
    await ctx.bot.database.set_setting(guild, "admin_role", role.id)


async def get_mod_role(ctx, guild):
    mod_id = await ctx.bot.database.get_setting(ctx.guild, "mod_role")
    if mod_id:
        return ctx.guild.get_role(int(mod_id))


async def set_mod_role(ctx, role):
    await ctx.bot.database.set_setting(ctx.guild, "mod_role", role.id)
