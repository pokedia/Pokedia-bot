import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class IncenseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def has_permissions(self, ctx):
        """Check if the user has Administrator perms or 'Incense Admin' role."""
        if ctx.author.guild_permissions.administrator:
            return True
        incense_admin_role = discord.utils.get(ctx.guild.roles, name="Incense Admin")
        return incense_admin_role in ctx.author.roles if incense_admin_role else False

    @commands.command(name="incensepause", aliases=["ip"])
    @is_not_suspended()
    async def pause(self, ctx, action: str = None):
        if not await self.has_permissions(ctx):
            return await ctx.send("You do not have permission to use this command.")

        server_id = ctx.guild.id
        channel_id = ctx.channel.id
        async with self.bot.db.pool.acquire() as conn:
            if action == "all":
                updated_rows = await conn.execute(
                    """
                    UPDATE incense SET paused = TRUE
                    WHERE server_id = $1 AND paused = FALSE
                    """,
                    server_id
                )
                incense_count = int(updated_rows.split()[-1])
                if incense_count > 0:
                    await ctx.send(f"Your {incense_count} incense has been paused.")
                else:
                    await ctx.send("No active incense found to pause.")
            else:
                updated_rows = await conn.execute(
                    """
                    UPDATE incense SET paused = TRUE
                    WHERE server_id = $1 AND channel_id = $2 AND paused = FALSE
                    """,
                    server_id, channel_id
                )
                if "UPDATE 1" in updated_rows:
                    await ctx.send("Incense in this channel has been paused.")
                else:
                    await ctx.send("No active incense found in this channel to pause.")

    @commands.command(name="incenseresume", aliases=["ir"])
    @is_not_suspended()
    async def resume(self, ctx, action: str = None):
        if not await self.has_permissions(ctx):
            return await ctx.send("You do not have permission to use this command.")

        server_id = ctx.guild.id
        channel_id = ctx.channel.id
        async with self.bot.db.pool.acquire() as conn:
            if action == "all":
                updated_rows = await conn.execute(
                    """
                    UPDATE incense SET paused = FALSE
                    WHERE server_id = $1 AND paused = TRUE
                    """,
                    server_id
                )
                incense_count = int(updated_rows.split()[-1])
                if incense_count > 0:
                    await ctx.send(f"Your {incense_count} incense has been resumed.")
                else:
                    await ctx.send("No paused incense found to resume.")
            else:
                updated_rows = await conn.execute(
                    """
                    UPDATE incense SET paused = FALSE
                    WHERE server_id = $1 AND channel_id = $2 AND paused = TRUE
                    """,
                    server_id, channel_id
                )
                if "UPDATE 1" in updated_rows:
                    await ctx.send("Incense in this channel has been resumed.")
                else:
                    await ctx.send("No paused incense found in this channel to resume.")

async def setup(bot):
    await bot.add_cog(IncenseCog(bot))
