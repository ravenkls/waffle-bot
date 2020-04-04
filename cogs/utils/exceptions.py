from discord.ext.commands import CommandError


class ModifyMemberError(CommandError):
    def __init__(self, action="modify"):
        super().__init__(f"You do not have permission to {action} that member.")


class BotHasLowRankError(CommandError):
    def __init__(self, action="modify"):
        super().__init__(f"I do not have permission to {action} that member.")