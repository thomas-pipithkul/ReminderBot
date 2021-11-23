import discord
from discord.ext import tasks, commands


class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.index = 0
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=5.0)
    async def printer(self):
        channel = self.bot.guilds[0].text_channels[0]
        await channel.send(self.index)
        print(self.index)
        self.index += 1

    @printer.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        print('Finished waiting')