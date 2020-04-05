from discord.ext.commands import CommandError


class CantModifyError(CommandError):
    def __init__(self):
        super().__init__(f"You do not have permission to do that.")


class BotHasLowRankError(CommandError):
    def __init__(self):
        super().__init__(f"I do not have permission to do that.")