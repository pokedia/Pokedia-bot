import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class MarketBuy(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db  # Database instance
        self.active_buys = {}  # Track active buys by user ID

    @commands.command(aliases=["mb"])
    @is_not_suspended()
    async def market_buy(self, ctx, market_id: int):
        """Allows users to buy Pokémon from the market."""

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot buy a Pokémon from the market while in an active trade.")
            return

        # Check if the user is already in the process of buying
        if ctx.author.id in self.active_buys:
            await ctx.send("You are already in the process of buying a Pokémon! Please complete your current purchase first.")
            return

        async with self.db.pool.acquire() as conn:
            # Fetch market entry
            market_entry = await conn.fetchrow("SELECT * FROM market WHERE marketid = $1", market_id)

            if not market_entry:
                await ctx.send(f"Market ID {market_id} not found.")
                return

            seller_id = market_entry["ownerid"]
            price = market_entry["price"]

            if ctx.author.id == seller_id:
                await ctx.send("You cannot buy your own Pokémon!")
                return

            # Fetch buyer's PokéCash
            buyer_data = await conn.fetchrow("SELECT pokecash FROM users WHERE userid = $1", ctx.author.id)

            if buyer_data["pokecash"] < price:
                await ctx.send("You do not have enough PokéCash!")
                return

            embed = discord.Embed(
                title="Market Purchase",
                description=f"Are you sure you want to buy **{market_entry['pokemon_name']}** "
                            f"(Level {market_entry['level']}, IV {market_entry['total_iv_percent']}%) "
                            f"for **{price}** PokéCash?",
                color=discord.Color.green()
            )

            # Mark user as active buyer
            self.active_buys[ctx.author.id] = market_id

            view = BuyConfirmView(ctx.author, market_id, self.db, self.bot, self)
            await ctx.send(embed=embed, view=view)

    def remove_active_buy(self, user_id):
        """Remove user from the active buys dictionary."""
        if user_id in self.active_buys:
            del self.active_buys[user_id]


class BuyConfirmView(discord.ui.View):
    """Handles market buy confirmation."""

    def __init__(self, buyer, market_id, db, bot, cog):
        super().__init__(timeout=60)
        self.buyer = buyer
        self.market_id = market_id
        self.db = db
        self.bot = bot  # Store the bot instance
        self.cog = cog # Reference to the cog to remove user from active buys

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.buyer:
            return await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)

        async with self.db.pool.acquire() as conn:
            # Start a transaction
            async with conn.transaction():
                # Fetch market entry again (in case it was sold)
                market_entry = await conn.fetchrow("SELECT * FROM market WHERE marketid = $1", self.market_id)

                if not market_entry:
                    return await interaction.response.send_message(
                        "❌ This Pokémon is no longer available in the market.", ephemeral=True)

                seller_id = market_entry["ownerid"]
                price = market_entry["price"]

                # Re-fetch buyer's PokéCash (in case it changed)
                buyer_data = await conn.fetchrow("SELECT pokecash FROM users WHERE userid = $1", interaction.user.id)

                if buyer_data["pokecash"] < price:
                    return await interaction.response.send_message(
                        "❌ You no longer have enough PokéCash to complete this purchase.", ephemeral=True)

                # Find the highest `pokemon_id` for this buyer
                highest_pokemon_id = await conn.fetchval(
                    "SELECT COALESCE(MAX(pokemon_id), 0) FROM users_pokemon WHERE userid = $1", interaction.user.id
                )

                next_pokemon_id = highest_pokemon_id + 1  # Set the next available ID

                # Deduct from buyer, add to seller
                await conn.execute("UPDATE users SET pokecash = pokecash - $1 WHERE userid = $2", price,
                                   interaction.user.id)
                await conn.execute("UPDATE users SET pokecash = pokecash + $1 WHERE userid = $2", price, seller_id)

                # Transfer Pokémon to buyer with correct `pokemon_id`
                await conn.execute(""" 
                    INSERT INTO users_pokemon (
                        userid, pokemon_id, unique_id, xp, pokemon_name, level, total_iv_percent, 
                        hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv, 
                        hp, attack, defense, spatk, spdef, speed, shiny, fusionable, 
                        selected, favorite, caught, max_xp, nickname
                    )
                    SELECT $1, $2, unique_id, xp, pokemon_name, level, total_iv_percent, 
                           hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv, 
                           hp, attack, defense, spatk, spdef, speed, shiny, fusionable, 
                           selected, favorite, FALSE, max_xp, nickname  -- Set caught = FALSE
                    FROM market WHERE marketid = $3
                """, interaction.user.id, next_pokemon_id, self.market_id)

                # Remove from market after successful transfer
                await conn.execute("DELETE FROM market WHERE marketid = $1", self.market_id)

                await interaction.response.send_message(
                    f"You have successfully purchased **{market_entry['pokemon_name']}**!", ephemeral=False)

                try:
                    # Notify the seller of the successful sale
                    seller = await self.bot.fetch_user(seller_id)
                    dm_message = (
                        f"Someone purchased your **{market_entry['pokemon_name']}** • **lvl {market_entry['level']}** • **IV% {market_entry['total_iv_percent']}**, "
                        f"you received {price} PokéCash!"
                    )
                    await seller.send(dm_message)
                except discord.Forbidden:
                    print(f"Could not DM seller {seller_id}, they might have DMs disabled.")

                # Remove user from active buys after successful purchase
                self.cog.remove_active_buy(interaction.user.id)

                # Stop any active confirmation process
                self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.buyer:
            return await interaction.response.send_message("Purchase cancelled.", ephemeral=True)

        # Remove user from active buys when cancelled
        self.cog.remove_active_buy(interaction.user.id)

        self.stop()


async def setup(bot):
    await bot.add_cog(MarketBuy(bot, bot.db))
