import discord
from discord.ext import commands
import asyncio
from utils.susp_check import is_not_suspended

class MarketOffer(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db  # Database instance

    @commands.command(aliases=["mo"])
    @is_not_suspended()
    async def market_offer(self, ctx, market_id: int, price: int):
        """Allows users to offer a price for a Pokémon in the market."""

        if price <= 0:
            await ctx.send("Offer price must be greater than 0 PokéCash.")
            return

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot offer for a Pokémon from the market while in an active trade.")
            return

        async with self.db.pool.acquire() as conn:
            market_entry = await conn.fetchrow("SELECT * FROM market WHERE marketid = $1", market_id)

            if not market_entry:
                await ctx.send(f"Market ID {market_id} not found.")
                return

            seller_id = market_entry["ownerid"]
            if ctx.author.id == seller_id:
                await ctx.send("You cannot offer on your own Pokémon!")
                return

            buyer_data = await conn.fetchrow("SELECT pokecash FROM users WHERE userid = $1", ctx.author.id)
            if buyer_data["pokecash"] < price:
                await ctx.send("You do not have enough PokéCash!")
                return

            # Check seller's toggle setting
            seller_data = await conn.fetchrow("SELECT toggle FROM users WHERE userid = $1", seller_id)
            if not seller_data or not seller_data["toggle"]:
                await ctx.send("The following seller does not accept offers!")
                return


            pokemon_name = market_entry["pokemon_name"]

            # Add emoji if shiny or fusionable
            if market_entry["shiny"]:
                pokemon_name = f"✨ {pokemon_name}"
            if market_entry["fusionable"]:
                pokemon_name = f"🧬 {pokemon_name}"

            # Ask buyer for confirmation using reactions
            confirm_embed = discord.Embed(
                title="Confirm Market Offer",
                description=f"React with ✅ to confirm or ❌ to cancel.\n\n"
                            f"Offering **{price}** PokéCash for **{pokemon_name}** • **lvl {market_entry['level']}** • **IV% {market_entry['total_iv_percent']}**",
                color=discord.Color.blue()
            )

            confirmation_msg = await ctx.send(embed=confirm_embed)
            await confirmation_msg.add_reaction("✅")
            await confirmation_msg.add_reaction("❌")


            def check(reaction, user):
                return user == ctx.author and reaction.message.id == confirmation_msg.id and str(reaction.emoji) in ["✅", "❌"]

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

                if str(reaction.emoji) == "❌":
                    await ctx.send("❌ Offer cancelled.")
                    return

            except asyncio.TimeoutError:
                await ctx.send("⏳ Offer confirmation timed out.")
                return

            # Add emoji before the Pokémon name
            pokemon_name = market_entry["pokemon_name"]

            if market_entry["shiny"]:
                pokemon_name = f"✨ {pokemon_name}"
            if market_entry["fusionable"]:
                pokemon_name = f"🧬 {pokemon_name}"

            # Full offer message
            offer_message = (
                f"Your offer on **{pokemon_name}** • **lvl {market_entry['level']}** • **IV% {market_entry['total_iv_percent']}** "
                f"has been sent to the seller."
            )

            await ctx.send(offer_message)

            # Add emoji before the Pokémon name
            pokemon_name = market_entry["pokemon_name"]

            if market_entry["shiny"]:
                pokemon_name = f"✨ {pokemon_name}"
            if market_entry["fusionable"]:
                pokemon_name = f"🧬 {pokemon_name}"

            # Send DM to the seller with buttons
            try:
                seller = await self.bot.fetch_user(seller_id)
                dm_embed = discord.Embed(
                    title="New Market Offer!",
                    description=f"{ctx.author.mention} has offered **{price}** PokéCash for your **{pokemon_name}** • **lvl {market_entry['level']}** • **IV% {market_entry['total_iv_percent']}**\n\n"
                                "Do you accept this offer?",
                    color=discord.Color.gold()
                )
                view = OfferConfirmView(ctx.author, seller_id, market_id, price, self.db, self.bot)

                if seller_data["toggle"]:
                    await seller.send(embed=dm_embed, view=view)
                else:
                    await ctx.send(f"⚠️ <@{seller_id}> has DMs disabled. They need to check here to accept/reject the offer.")

            except discord.Forbidden:
                await ctx.send(f"⚠️ <@{seller_id}> has DMs disabled. They need to check here to accept/reject the offer.")
class OfferConfirmView(discord.ui.View):
    def __init__(self, buyer, seller_id, market_id, price, db, bot):
        super().__init__(timeout=60)
        self.buyer = buyer
        self.seller_id = seller_id
        self.market_id = market_id
        self.price = price
        self.db = db
        self.bot = bot

    @discord.ui.button(label="Accept Offer", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.seller_id:
            return await interaction.response.send_message("You are not the seller!", ephemeral=True)

        async with self.db.pool.acquire() as conn:
            market_entry = await conn.fetchrow("SELECT * FROM market WHERE marketid = $1", self.market_id)
            if not market_entry:
                return await interaction.response.send_message("This Pokémon is no longer available.")

            buyer_data = await conn.fetchrow("SELECT pokecash FROM users WHERE userid = $1", self.buyer.id)
            if buyer_data["pokecash"] < self.price:
                return await interaction.response.send_message("The buyer no longer has enough PokéCash!")

            # Transfer funds
            await conn.execute("UPDATE users SET pokecash = pokecash - $1 WHERE userid = $2", self.price, self.buyer.id)
            await conn.execute("UPDATE users SET pokecash = pokecash + $1 WHERE userid = $2", self.price, self.seller_id)

            # Assign new Pokémon ID
            highest_pokemon_id = await conn.fetchval(
                "SELECT COALESCE(MAX(pokemon_id), 0) FROM users_pokemon WHERE userid = $1", self.buyer.id
            )
            next_pokemon_id = highest_pokemon_id + 1

            # Transfer Pokémon to buyer
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
                       selected, favorite, FALSE, max_xp, nickname
                FROM market WHERE marketid = $3
            """, self.buyer.id, next_pokemon_id, self.market_id)

            await conn.execute("DELETE FROM market WHERE marketid = $1", self.market_id)

            pokemon_name = market_entry["pokemon_name"]

            # Add emoji if shiny or fusionable
            if market_entry["shiny"]:
                pokemon_name = f"✨ {pokemon_name}"
            if market_entry["fusionable"]:
                pokemon_name = f"🧬 {pokemon_name}"

            try:
                buyer = await self.bot.fetch_user(self.buyer.id)
                if buyer:
                    dm_embed = discord.Embed(
                        title="Market Offer Accepted!",
                        description=f"You have successfully purchased **{pokemon_name}** • **lvl {market_entry['level']}** • **IV% {market_entry['total_iv_percent']}** for **{self.price}** PokéCash.",
                        color=discord.Color.green()
                    )
                    await buyer.send(embed=dm_embed)
                    print(f"✅ Purchase confirmation sent to {buyer}")
            except discord.Forbidden:
                print(f"❌ Could not DM buyer (ID: {self.buyer.id}) - DMs are closed.")

            await interaction.response.send_message("✅ Offer accepted! The buyer has been notified in DMs.")
            self.stop()

    @discord.ui.button(label="Reject Offer", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.seller_id:
            return await interaction.response.send_message("You are not the seller!", ephemeral=True)

        async with self.db.pool.acquire() as conn:
            market_entry = await conn.fetchrow("SELECT * FROM market WHERE marketid = $1", self.market_id)

        pokemon_name = market_entry["pokemon_name"]

        # Add emoji if shiny or fusionable
        if market_entry["shiny"]:
            pokemon_name = f"✨ {pokemon_name}"
        if market_entry["fusionable"]:
            pokemon_name = f"🧬 {pokemon_name}"

        try:
            buyer = await self.bot.fetch_user(self.buyer.id)
            if buyer:
                reject_embed = discord.Embed(
                    title="Market Offer Rejected",
                    description=f"The seller has rejected your offer for **{pokemon_name}** • **lvl {market_entry['level']}** • **IV% {market_entry['total_iv_percent']}** of **{self.price}** PokéCash.",
                    color=discord.Color.red()
                )
                await buyer.send(embed=reject_embed)
                print(f"✅ Rejection notice sent to {buyer}")
        except discord.Forbidden:
            print(f"❌ Could not DM buyer (ID: {self.buyer.id}) - DMs are closed.")

        await interaction.response.send_message("❌ Offer rejected. The buyer has been notified.")
        self.stop()


async def setup(bot):
    await bot.add_cog(MarketOffer(bot, bot.db))

