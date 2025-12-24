import discord
from discord.ext import commands
import os

class ReloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reload")
    @commands.is_owner()  # only bot owner can use this
    async def reload(self, ctx, filename: str):
        """Reloads a cog from the commands folder."""
        cog_path = f"commands.{filename}"

        if not os.path.isfile(f"commands/{filename}.py"):
            return await ctx.send(f"❌ `{filename}.py` not found in `commands/` folder.")

        try:
            await self.bot.reload_extension(cog_path)
            await ctx.send(f"✅ Reloaded `{filename}.py` successfully.")
        except commands.ExtensionNotLoaded:
            try:
                await self.bot.load_extension(cog_path)
                await ctx.send(f"✅ Loaded `{filename}.py` (was not previously loaded).")
            except Exception as e:
                await ctx.send(f"❌ Failed to load `{filename}.py`.\n```{e}```")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload `{filename}.py`.\n```{e}```")

async def setup(bot):
    await bot.add_cog(ReloadCog(bot))

