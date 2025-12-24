import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class PingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @is_not_suspended()
    async def ping(self, ctx):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)  # Convert to milliseconds
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot latency: `{latency}ms`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PingCommand(bot))
