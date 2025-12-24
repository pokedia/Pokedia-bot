import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["inv"])
    @is_not_suspended()
    async def inventory(self, ctx):
        user_id = ctx.author.id

        try:
            query = "SELECT item_name, value FROM inventory WHERE userid = $1"
            rows = await self.bot.db.fetch(query, user_id)  # Now this works!

            if not rows:
                embed = discord.Embed(title="Your Inventory", description="You have no items.", color=discord.Color.red())
            else:
                embed = discord.Embed(title="Your Inventory", color=discord.Color.blue())
                inventory_text = "\n\n".join([f"• **{row['item_name']}:** {row['value']}" for row in rows])
                embed.description = inventory_text

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Error fetching inventory: {e}")

async def setup(bot):
    await bot.add_cog(Inventory(bot))

