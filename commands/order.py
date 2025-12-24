import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended


class OrderCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.order = {}  # To store the current order preference

    @commands.command(name="order")
    @is_not_suspended()
    async def order_command(self, ctx, *, order: str):
        """Sets the sorting order for Pokémon inventory."""
        user_id = ctx.author.id

        if order not in ["iv-", "iv+", "level-", "level+", "id-", "id+"]:
            await ctx.send("Invalid order! Use `iv-`, `iv+`, `level-`, `level+`, `id-`, or `id+`.")
            return

        # Store the order preference for the user
        self.order[user_id] = order
        await ctx.send(f"Sorting order set to **{order}**.")

    def sort_inventory(self, inventory, order):
        if order is None:
            return inventory  # No sorting needed if no order is set

        if order == "iv-":
            return sorted(inventory, key=lambda p: p["total_iv_percent"], reverse=True)
        elif order == "iv+":
            return sorted(inventory, key=lambda p: p["total_iv_percent"])
        elif order == "level-":
            return sorted(inventory, key=lambda p: p["level"], reverse=True)
        elif order == "level+":
            return sorted(inventory, key=lambda p: p["level"])
        elif order == "id-":
            return sorted(inventory, key=lambda p: p["pokemon_id"], reverse=True)
        elif order == "id+":
            return sorted(inventory, key=lambda p: p["pokemon_id"])


async def setup(bot):
    await bot.add_cog(OrderCommands(bot))
