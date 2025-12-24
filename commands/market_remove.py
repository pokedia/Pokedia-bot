import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class MarketRemove(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.command(aliases=["mr"])
    @is_not_suspended()
    async def market_remove(self, ctx, market_id: int):
        """Removes a Pokémon from the market (if you're the seller)."""

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot remove  a Pokémon from the market while in an active trade.")
            return

        market_entry = await self.db.fetchrow("SELECT * FROM market WHERE marketid = $1", market_id)

        if not market_entry:
            await ctx.send("No market listing found with that ID!")
            return

        if market_entry["ownerid"] != ctx.author.id:
            await ctx.send("You can only remove your own listings from the market!")
            return

        prefix = "✨" if market_entry["shiny"] else "🧪" if market_entry["fusionable"] else ""
        view = RemoveConfirmView(ctx.author.id, market_entry, self.db)
        await ctx.send(
            f"Are you sure you want to remove **{prefix}{market_entry['pokemon_name']}** • **Level {market_entry['level']}** • **{market_entry['total_iv_percent']}% IV** from the market?",
            view=view
        )


class RemoveConfirmView(discord.ui.View):
    def __init__(self, user_id, pokemon_data, db):
        super().__init__()
        self.user_id = user_id
        self.pokemon_data = pokemon_data
        self.db = db

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("You cannot confirm this action.", ephemeral=True)

        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    # Check if Pokémon still exists in the market
                    market_check = await conn.fetchrow(
                        "SELECT marketid FROM market WHERE marketid = $1", self.pokemon_data["marketid"]
                    )
                    if not market_check:
                        return await interaction.response.send_message(
                            "This Pokémon is no longer in the market.", ephemeral=True
                        )

                    # Get the next available pokemon_id for this user
                    last_id_row = await conn.fetchrow(
                        "SELECT MAX(pokemon_id) FROM users_pokemon WHERE userid = $1", self.user_id
                    )
                    next_pokemon_id = (last_id_row["max"] or 0) + 1

                    # Re-insert into inventory
                    await conn.execute(
                        """
                        INSERT INTO users_pokemon (
                            pokemon_id, userid, xp, pokemon_name, level, total_iv_percent,
                            hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                            hp, attack, defense, spatk, spdef, speed,
                            shiny, fusionable, selected, favorite,
                            unique_id, nickname, max_xp
                        )
                        VALUES (
                            $1, $2, $3, $4, $5, $6,
                            $7, $8, $9, $10, $11, $12,
                            $13, $14, $15, $16, $17, $18,
                            $19, $20, $21, $22,
                            $23, $24, $25
                        )
                        """,
                        next_pokemon_id, self.pokemon_data["ownerid"], self.pokemon_data["xp"],
                        self.pokemon_data["pokemon_name"], self.pokemon_data["level"],
                        self.pokemon_data["total_iv_percent"],
                        self.pokemon_data["hp_iv"], self.pokemon_data["attack_iv"], self.pokemon_data["defense_iv"],
                        self.pokemon_data["spatk_iv"], self.pokemon_data["spdef_iv"], self.pokemon_data["speed_iv"],
                        self.pokemon_data["hp"], self.pokemon_data["attack"], self.pokemon_data["defense"],
                        self.pokemon_data["spatk"], self.pokemon_data["spdef"], self.pokemon_data["speed"],
                        self.pokemon_data["shiny"], self.pokemon_data["fusionable"], False,
                        self.pokemon_data["favorite"],
                        self.pokemon_data["unique_id"], self.pokemon_data["nickname"], self.pokemon_data["max_xp"]
                    )

                    await conn.execute("DELETE FROM market WHERE marketid = $1", self.pokemon_data["marketid"])

            await interaction.response.send_message(
                f"Pokémon **{self.pokemon_data['pokemon_name']}** has been removed from the market and returned to your inventory."
            )
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            self.stop()

        except Exception as e:
            print(f"Error removing from market: {e}")
            await interaction.response.send_message("An error occurred while removing the Pokémon.", ephemeral=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("You cannot decline this action.", ephemeral=True)

        await interaction.response.send_message("The Pokémon was not removed from the market.", ephemeral=False)
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

async def setup(bot):
    db = bot.db
    await bot.add_cog(MarketRemove(bot, db))
