import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended


class MarketAdd(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.active_users = set()  # Track users who are in the middle of a market add

    @commands.command(aliases=["ma"])
    @is_not_suspended()
    async def market_add(self, ctx, pokemon_id: int, price: int):
        """Adds a Pokémon to the market."""

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot add a Pokémon to the market while in an active trade.")
            return

        # Check if the price is above 0
        if price <= 0:
            await ctx.send("❌ The price must be greater than 0 PokéCash.")
            return

        # Check if the user is already adding a Pokémon to the market
        if ctx.author.id in self.active_users:
            await ctx.send("You're already adding a Pokémon to the market. Please confirm or decline that first.")
            return

        # Fetch the Pokémon from the database
        user_pokemon = await self.db.fetchrow("SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                                              ctx.author.id, pokemon_id)
        if not user_pokemon:
            await ctx.send("Invalid Pokémon ID!")
            return

        if user_pokemon["selected"]:
            await ctx.send("You cannot add a selected Pokémon to the market!")
            return

        # Add the user to the active users set to prevent them from adding another Pokémon
        self.active_users.add(ctx.author.id)

        # Determine the Pokémon's prefix (Shiny or Fusionable)
        prefix = "✨" if user_pokemon["shiny"] else "🧪" if user_pokemon["fusionable"] else ""

        # Create a confirmation view for the user to confirm the market add
        view = ConfirmView(ctx.author.id, user_pokemon, price, self.db, self.bot, self.active_users)
        await ctx.send(
            f"Are you sure you want to add **{prefix}{user_pokemon['pokemon_name']}** • **Level {user_pokemon['level']}** • **{user_pokemon['total_iv_percent']}% IV** for **{price}** PokéCash to the market?",
            view=view
        )


class ConfirmView(discord.ui.View):
    def __init__(self, user_id, pokemon, price, db, bot, active_users):
        super().__init__()
        self.user_id = user_id
        self.pokemon = pokemon
        self.price = price
        self.db = db
        self.bot = bot  # Reference to the bot
        self.active_users = active_users  # Reference to active_users from MarketAdd

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("You cannot confirm this request.", ephemeral=True)

        try:
            async with self.db.pool.acquire() as conn:
                # ✅ Pre-check: Ensure the Pokémon is still in the user's inventory
                result = await conn.fetchrow(
                    "SELECT 1 FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                    self.user_id, self.pokemon["pokemon_id"]
                )

                if not result:
                    return await interaction.response.send_message(
                        "This Pokémon is no longer in your inventory.", ephemeral=True
                    )

                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO market (
                            ownerid, price, xp, pokemon_name, level, total_iv_percent,
                            hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                            hp, attack, defense, spatk, spdef, speed,
                            shiny, fusionable, selected, favorite, unique_id, nickname, max_xp
                        )
                        VALUES (
                            $1, $2, $3, $4, $5, $6,
                            $7, $8, $9, $10, $11, $12,
                            $13, $14, $15, $16, $17, $18,
                            $19, $20, $21, $22, $23, $24, $25
                        )
                        """,
                        self.user_id, self.price, self.pokemon["xp"], self.pokemon["pokemon_name"],
                        self.pokemon["level"], self.pokemon["total_iv_percent"],
                        self.pokemon["hp_iv"], self.pokemon["attack_iv"], self.pokemon["defense_iv"],
                        self.pokemon["spatk_iv"], self.pokemon["spdef_iv"], self.pokemon["speed_iv"],
                        self.pokemon["hp"], self.pokemon["attack"], self.pokemon["defense"], self.pokemon["spatk"],
                        self.pokemon["spdef"], self.pokemon["speed"],
                        self.pokemon["shiny"], self.pokemon["fusionable"], self.pokemon["selected"],
                        self.pokemon["favorite"], self.pokemon["unique_id"], self.pokemon["nickname"],
                        self.pokemon["max_xp"]
                    )

                    await conn.execute(
                        "DELETE FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                        self.user_id, self.pokemon["pokemon_id"]
                    )

            await interaction.response.send_message(
                f"Pokémon **{self.pokemon['pokemon_name']}** successfully added to the market for **{self.price}** PokéCash!",
                ephemeral=False
            )

        except Exception as e:
            import traceback
            print(f"Error in confirm interaction: {e}")
            traceback.print_exc()
            await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

        finally:
            self.active_users.discard(self.user_id)
            self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("You cannot decline this request.", ephemeral=True)

        await interaction.response.send_message("The Pokémon was not added to the market.", ephemeral=False)

        # Clean up user state on decline
        self.active_users.discard(self.user_id)  # Ensure the user is removed from active users
        self.stop()

async def setup(bot):
    await bot.add_cog(MarketAdd(bot, bot.db))


