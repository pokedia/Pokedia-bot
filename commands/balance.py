import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_balance(self, user_id):
        query = "SELECT pokecash, shards FROM users WHERE userid = $1"
        async with self.bot.db.pool.acquire() as conn:
            return await conn.fetchrow(query, user_id)

    @commands.command(name="balance", aliases=["bal"])
    @is_not_suspended()
    async def balance_command(self, ctx):
        """Shows the user's balance (Pokécash & Shards)."""
        user_id = ctx.author.id
        user = ctx.author

        try:
            balance = await self.get_user_balance(user_id)
            if not balance:
                await ctx.send("You don't have an account yet!")
                return
        except Exception as e:
            print(f"Error retrieving user balance: {e}")
            await ctx.send("An error occurred while retrieving your balance.")
            return

        pokecash = balance["pokecash"]
        shards = balance["shards"]

        embed = discord.Embed(
            title=f"**{user.name}'s Balance**",
            color=discord.Color.gold()
        )
        embed.add_field(name="**Pokécash**", value=f"{pokecash:,} cash", inline=True)
        embed.add_field(name="**Shards**", value=f"{shards:,}", inline=True)

        # Set thumbnail to user's avatar or default Discord avatar
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        embed.set_thumbnail(url=avatar_url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Balance(bot))
