from discord.ext.commands import CommandError


class ModifyMemberError(CommandError):
    def __init__(self):
        super().__init__("You do not have permission to modify that member.")
