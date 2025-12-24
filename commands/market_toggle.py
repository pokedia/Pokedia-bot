import discord
from discord.ext import commands


class MarketCommands(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db  # Use bot's database connection

    @commands.command(name='mt')
    async def market_toggle(self, ctx, status: str = None):
        """Toggle market status with !mt true/false."""
        if status not in ['true', 'false']:
            await ctx.send("Please specify `true` or `false`.\nUsage: `!mt true` or `!mt false`")
            return

        user_id = ctx.author.id
        toggle_value = status.lower() == 'true'

        # Update the toggle column in the database
        await self.db.execute("UPDATE users SET toggle = $1 WHERE userid = $2", toggle_value, user_id)

        status_msg = "enabled" if toggle_value else "disabled"
        await ctx.send(f"Market toggle has been **{status_msg}** for {ctx.author.mention}.")

    @commands.command(name='market_dm', aliases=['md'])
    async def market_dm(self, ctx, market_id: int = None, *, message: str = None):
        """Send a DM to the Pokémon owner if they have market_toggled enabled."""
        if market_id is None or message is None:
            await ctx.send("Usage: `!market_dm <market_id> <message>` or `!md <market_id> <message>`")
            return

        # Fetch the market listing details
        market_data = await self.db.fetchrow(
            "SELECT ownerid, pokemon_name, total_iv_percent FROM market WHERE marketid = $1", market_id
        )

        if not market_data:
            await ctx.send(f"Market ID `{market_id}` does not exist.")
            return

        owner_id = market_data["ownerid"]
        pokemon_name = market_data["pokemon_name"]
        iv_percent = market_data["total_iv_percent"]

        # Check if the owner has market DMs enabled
        toggle_status = await self.db.fetchval("SELECT toggle FROM users WHERE userid = $1", owner_id)

        if not toggle_status:
            await ctx.send(f"The owner of Market ID `{market_id}` has not enabled DMs for market messages.")
            return

        # Fetch user object
        try:
            owner = await self.bot.fetch_user(owner_id)
        except discord.NotFound:
            await ctx.send(f"Could not find the user with ID `{owner_id}`.")
            return
        except Exception as e:
            await ctx.send(f"An error occurred while fetching the user: {e}")
            return

        # DM message format
        dm_message = (
            f"Your **{pokemon_name}** ({iv_percent}% IV) received a message from **{ctx.author.name}**:\n"
            f"➤ {message}"
        )

        # Send the DM
        try:
            await owner.send(dm_message)
            await ctx.send(f"Message successfully sent to the owner of Market ID `{market_id}`.")
        except discord.Forbidden:
            await ctx.send(f"Could not send DM to the owner of Market ID `{market_id}`. They might have DMs disabled.")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")


async def setup(bot):
    await bot.add_cog(MarketCommands(bot, bot.db))
