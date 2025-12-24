import discord
from discord.ext import commands

# 🔒 Users allowed to run this command
ALLOWED_USERS = {
    760720549092917248,  # replace with real IDs
    688983124868202496,
}

class Unsuspend(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="unsuspend")
    async def unsuspend(self, ctx, userid: int):
        # Permission check
        if ctx.author.id not in ALLOWED_USERS:
            await ctx.send("❌ You are not allowed to use this command.")
            return

        try:
            # Update the user: remove suspension
            await self.bot.db.execute(
                """
                UPDATE users
                SET suspended = $1, reason = $2
                WHERE userid = $3
                """,
                False,
                "",
                userid
            )

            # Check if the user exists
            user = await self.bot.db.fetchrow(
                "SELECT userid FROM users WHERE userid = $1",
                userid
            )

            if not user:
                await ctx.send("⚠️ User not found in database.")
                return

            await ctx.send(f"✅ User `{userid}` has been unsuspended.")

        except Exception as e:
            await ctx.send("❌ An error occurred while unsuspending the user.")
            print("Unsuspend error:", e)


async def setup(bot):
    await bot.add_cog(Unsuspend(bot))
