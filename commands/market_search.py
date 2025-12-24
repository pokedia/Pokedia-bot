import discord
from discord.ext import commands
import asyncpg
from utils.susp_check import is_not_suspended

class MarketSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["ms"])
    @is_not_suspended()
    async def market_search(self, ctx):
        """Displays Pokémon listed in the market without filters."""

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot search a  Pokémon from the market while in an active trade.")
            return

        market_data = await self.load_market()
        if not market_data:
            await ctx.send("The market is empty!")
            return

        view = MarketView(self, ctx.author, market_data)
        await ctx.send(embed=await view.generate_embed(), view=view)

    async def load_market(self):
        """Fetches market data from PostgreSQL."""
        if not hasattr(self.bot, "db") or self.bot.db.pool is None:
            print("Error: Database pool is not initialized!")
            return {}

        query = """
        SELECT marketid, ownerid, price, pokemon_name, level, total_iv_percent, shiny
        FROM market
        ORDER BY marketid DESC;  -- Order by marketid to get newest listings first
        """
        try:
            async with self.bot.db.pool.acquire() as conn:
                rows = await conn.fetch(query)

            market_data = {
                str(row['marketid']): {
                    "owner_id": row['ownerid'],
                    "price": row['price'],
                    "pokemon": {
                        "name": row['pokemon_name'],
                        "level": row['level'],
                        "iv": row['total_iv_percent'],
                        "is_shiny": row['shiny']
                    }
                }
                for row in rows
            }
            return market_data
        except Exception as e:
            print(f"Database error: {e}")
            return {}

class MarketView(discord.ui.View):
    def __init__(self, cog, user, market_data, page=0):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.market_data = market_data
        self.page = page
        self.per_page = 20  # Set items per page
        self.update_buttons()

    async def generate_embed(self):
        """Generates the market embed with pagination."""
        embed = discord.Embed(title="Pokémon Marketplace", color=discord.Color.gold())
        start = self.page * self.per_page
        end = start + self.per_page
        market_items = list(self.market_data.items())[start:end]

        if not market_items:
            embed.description = "No Pokémon available."
        else:
            sprites_cog = self.cog.bot.get_cog("Sprites")  # Get the Sprites cog

            for market_id, listing in market_items:
                pokemon = listing["pokemon"]
                name = pokemon["name"]
                level = pokemon["level"]
                iv = pokemon["iv"]
                price = f"{listing['price']:,}"
                is_shiny = pokemon.get("is_shiny", False)
                prefix = "✨" if is_shiny else ""

                # Fetch Pokémon emoji from the Sprites cog
                emoji = await sprites_cog.get_pokemon_emoji(name) if sprites_cog else name

                embed.add_field(
                    name=f"`{market_id}`    {emoji} {prefix}**{name}**  •  Level {level}   •   IV: {iv}%   •    **{price} PokéCash**",
                    value="",
                    inline=False
                )

        total_pages = max(1, (len(self.market_data) // self.per_page) + (
            1 if len(self.market_data) % self.per_page else 0))
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages}")
        return embed

    def update_buttons(self):
        """Updates the navigation buttons' state."""
        total_pages = max(1, (len(self.market_data) // self.per_page) + (
            1 if len(self.market_data) % self.per_page else 0))
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page + 1 >= total_pages

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("You can't use this navigation!", ephemeral=True)

        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed= await self.generate_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("You can't use this navigation!", ephemeral=True)

        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed= await self.generate_embed(), view=self)

async def setup(bot):
    await bot.add_cog(MarketSearch(bot))
