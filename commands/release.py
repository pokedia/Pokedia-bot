import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.susp_check import is_not_suspended


class ReleaseView(View):
    def __init__(self, bot, user_id, pokemon_id, pokemon_name, level, iv, is_shiny, is_fusionable):
        super().__init__(timeout=30)
        self.bot = bot
        self.user_id = user_id
        self.pokemon_id = pokemon_id
        self.pokemon_name = pokemon_name
        self.level = level
        self.iv = iv
        self.is_shiny = is_shiny
        self.is_fusionable = is_fusionable

    async def delete_pokemon(self, interaction: discord.Interaction):
        async with self.bot.db.pool.acquire() as conn:
            # Check if the Pokémon still exists
            result = await conn.fetchrow(
                "SELECT pokemon_name, level, total_iv_percent FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                self.user_id,
                self.pokemon_id
            )

            if not result:
                await interaction.response.send_message(
                    "That Pokémon no longer exists or was already released!",
                    ephemeral=True
                )
                return

            # Extract values for confirmation message
            name = result["pokemon_name"]
            level = result["level"]
            iv_percent = round(result["total_iv_percent"], 2)

            # Delete the Pokémon and update cash
            await conn.execute(
                "DELETE FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                self.user_id,
                self.pokemon_id
            )
            await conn.execute(
                "UPDATE users SET pokecash = pokecash + 2 WHERE userid = $1",
                self.user_id
            )

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Pokémon Released!",
                description=f"{name} • Lvl {level} • {iv_percent}% IV was released. You received 2 PokéCash!",
                color=discord.Color.green()
            ),
            view=None
        )

    def get_display_name(self):
        name = self.pokemon_name
        if self.is_shiny:
            name = f"✨ {name}"
        if self.is_fusionable:
            name = f"🧬 {name}"
        return f"**{name}**"

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't for you!", ephemeral=True)
        await self.delete_pokemon(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't for you!", ephemeral=True)
        await interaction.response.edit_message(embed=discord.Embed(
            title="Release Cancelled",
            description=f"{self.get_display_name()} • Lvl {self.level} • {self.iv}% IV was not released.",
            color=discord.Color.red()
        ), view=None)


class Release(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="release")
    @is_not_suspended()
    async def release_command(self, ctx, pokemon_id: int):
        """Releases a specific Pokémon from the user's collection."""
        user_id = ctx.author.id

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot release a pokemon in an active trade.")
            return

        async with self.bot.db.pool.acquire() as conn:
            pokemon = await conn.fetchrow("SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2", user_id,
                                          pokemon_id)
            if not pokemon:
                return await ctx.send("Invalid Pokémon ID.")

            if pokemon["selected"] or pokemon["favorite"]:
                return await ctx.send("You cannot release a selected or favorite Pokémon!")

        pokemon_name = pokemon["pokemon_name"]
        level = pokemon["level"]
        iv = pokemon["total_iv_percent"]
        is_shiny = pokemon["shiny"]
        is_fusionable = pokemon["fusionable"]

        name_display = f"**{'✨ ' if is_shiny else ''}{'🧬 ' if is_fusionable else ''}{pokemon_name}**"

        embed = discord.Embed(
            title="Confirm Release",
            description=f"Are you sure you want to release {name_display} • Lvl {level} • {iv}% IV?",
            color=discord.Color.orange()
        )

        view = ReleaseView(self.bot, user_id, pokemon_id, pokemon_name, level, iv, is_shiny, is_fusionable)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Release(bot))

