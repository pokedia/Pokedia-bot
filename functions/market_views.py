import discord

class BuyConfirmView(discord.ui.View):
    """Handles market buy confirmation."""

    def __init__(self, buyer, market_id, cog):
        super().__init__(timeout=60)
        self.buyer = buyer
        self.market_id = str(market_id)
        self.cog = cog

@discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user != self.buyer:
        return await interaction.response.send_message("This is not your purchase!", ephemeral=True)

    # Load market data again in case it changed
    market_data = self.cog.load_market()
    if self.market_id not in market_data:
        await interaction.response.send_message("This item is no longer available.", ephemeral=True)
        return

    # Get transaction details
    entry = market_data[self.market_id]
    price = entry["price"]
    pokemon = entry["pokemon"]
    seller_id = entry["owner_id"]

    # Fetch buyer & seller data
    buyer_data = self.cog.db.get_user(interaction.user.id)
    seller_data = self.cog.db.get_user(seller_id)

    # Check if buyer has enough money
    if buyer_data["pokecash"] < price:
        await interaction.response.send_message("You do not have enough PokéCash!", ephemeral=True)
        return

    # Deduct money from buyer and add to seller
    buyer_data["pokecash"] -= price
    seller_data["pokecash"] += price

    # Ensure the buyer has a Pokémon inventory list
    if "pokemons" not in buyer_data:
        buyer_data["pokemons"] = []

    # Transfer the Pokémon to the buyer's inventory
    buyer_data["pokemons"].append(pokemon)

    # Save the updated user data
    self.cog.db.update_user(interaction.user.id, buyer_data)
    self.cog.db.update_user(seller_id, seller_data)

    # Remove Pokémon from market
    del market_data[self.market_id]
    self.cog.save_market(market_data)

    # Confirm purchase
    await interaction.response.send_message(f"You have successfully purchased **{pokemon['name']}**!", ephemeral=True)
    self.stop()
