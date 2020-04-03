

async def get_admin_role(database, guild):
    admin_id = await database.get_setting(guild, "admin_role")
    if admin_id:
        return guild.get_role(int(admin_id))


async def set_admin_role(database, guild, role):
    await database.set_setting(guild, "admin_role", role.id)


async def get_mod_role(database, guild):
    mod_id = await database.get_setting(guild, "mod_role")
    if mod_id:
        return guild.get_role(int(mod_id))


async def set_mod_role(database, guild, role):
    await database.set_setting(guild, "mod_role", role.id)
