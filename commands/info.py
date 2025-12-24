import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.susp_check import is_not_suspended

class PokemonInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class InfoView(View):
        def __init__(self, bot, user_id, pokemon_id):
            super().__init__()
            self.bot = bot
            self.user_id = user_id
            self.pokemon_id = str(pokemon_id)

        async def fetch_pokemon(self, user_id, pokemon_id):
            query = """
                SELECT * FROM users_pokemon 
                WHERE userid = $1 AND pokemon_id = $2
            """
            async with self.bot.db.pool.acquire() as conn:
                return await conn.fetchrow(query, int(user_id), int(pokemon_id))

        async def update_embed(self, target, new_id):
            user_id = self.user_id
            pokemon_data = await self.fetch_pokemon(user_id, new_id)

            if not pokemon_data:
                if isinstance(target, discord.Interaction):
                    await target.response.send_message(f"No Pokémon found with ID {new_id}.", ephemeral=True)
                else:
                    await target.send(f"No Pokémon found with ID {new_id}.")
                return

            name = pokemon_data["pokemon_name"]
            level = pokemon_data["level"]
            xp = pokemon_data["xp"]
            max_xp = pokemon_data["max_xp"]  # Fetch max XP from the database
            total_iv = pokemon_data["total_iv_percent"]
            is_shiny = pokemon_data["shiny"]
            unique_id = pokemon_data["unique_id"]  # Fetch the unique ID
            is_favorite = pokemon_data["favorite"]
            nickname = pokemon_data["nickname"]

            stats = {
                "hp": {"value": pokemon_data["hp"], "iv": pokemon_data["hp_iv"]},
                "attack": {"value": pokemon_data["attack"], "iv": pokemon_data["attack_iv"]},
                "defense": {"value": pokemon_data["defense"], "iv": pokemon_data["defense_iv"]},
                "special-attack": {"value": pokemon_data["spatk"], "iv": pokemon_data["spatk_iv"]},
                "special-defense": {"value": pokemon_data["spdef"], "iv": pokemon_data["spdef_iv"]},
                "speed": {"value": pokemon_data["speed"], "iv": pokemon_data["speed_iv"]},
            }

            display_name = f"✨ {name}" if is_shiny else name
            if nickname:  # Append nickname if it exists
                display_name += f' "{nickname}"'
            if is_favorite:  # Append 💖 if it's a favorite Pokémon
                display_name += " 💖"


            image_name = name.lower().replace(" ", "-")
            image_url = (
                f"https://github.com/pokedia/images/blob/main/pokemon_shiny/{image_name}.png?raw=true&v=4"
                if is_shiny
                else f"https://github.com/pokedia/images/blob/main/pokemon_images/{image_name}.png?raw=true&v=5"
            )

            embed = discord.Embed(
                title=f"Level {level} {display_name}",
                color=discord.Color.gold() if is_shiny else discord.Color.blue()
            )
            embed.add_field(name="XP:", value=f"{xp}/{max_xp}", inline=True)  # Updated to show XP/max XP
            embed.add_field(
                name="Stats",
                value=(f"**HP**: {stats['hp']['value']} - IV {stats['hp']['iv']}/31\n"
                       f"**Attack**: {stats['attack']['value']} - IV {stats['attack']['iv']}/31\n"
                       f"**Defense**: {stats['defense']['value']} - IV {stats['defense']['iv']}/31\n"
                       f"**Sp. Atk**: {stats['special-attack']['value']} - IV {stats['special-attack']['iv']}/31\n"
                       f"**Sp. Def**: {stats['special-defense']['value']} - IV {stats['special-defense']['iv']}/31\n"
                       f"**Speed**: {stats['speed']['value']} - IV {stats['speed']['iv']}/31\n"
                       f"**Total IV**: {total_iv}%"),
                inline=False
            )
            embed.set_footer(text=f"Displaying Pokémon ID: {new_id}\nUnique ID: {unique_id}")  # Add Unique ID here
            embed.set_thumbnail(url=target.user.display_avatar.url if isinstance(target,
                                                                                 discord.Interaction) else target.author.display_avatar.url)
            embed.set_image(url=image_url)

            self.pokemon_id = new_id

            if isinstance(target, discord.Interaction):
                await target.response.edit_message(embed=embed, view=self)
            else:
                await target.send(embed=embed, view=self)

        @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
        async def previous_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't use this button!", ephemeral=True)
                return
            new_id = max(int(self.pokemon_id) - 1, 1)  # Prevent negative IDs
            await self.update_embed(interaction, int(new_id))

        @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
        async def next_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't use this button!", ephemeral=True)
                return
            new_id = int(self.pokemon_id) + 1
            await self.update_embed(interaction, int(new_id))

    @commands.command(name="info", aliases=["i", "I"])
    @is_not_suspended()
    async def info_command(self, ctx, pokemon_id: str = None):
        user_id = ctx.author.id

        async with self.bot.db.pool.acquire() as conn:
            if pokemon_id is None:
                # Fetch selected Pokémon
                query = """
                    SELECT pokemon_id FROM users_pokemon 
                    WHERE userid = $1 AND selected = TRUE
                """
                pokemon_id = await conn.fetchval(query, user_id)

                if not pokemon_id:
                    await ctx.send("You don't have a selected Pokémon. Use `!select <ID>` to set one.")
                    return

            elif pokemon_id.lower() in ["l", "latest"]:
                # Fetch the Pokémon with the max ID for the user
                query = """
                    SELECT MAX(pokemon_id) FROM users_pokemon 
                    WHERE userid = $1
                """
                pokemon_id = await conn.fetchval(query, user_id)

                if not pokemon_id:
                    await ctx.send("You don't have any Pokémon.")
                    return

        # Convert pokemon_id to integer before querying
        pokemon_id = int(pokemon_id)

        # Fetch Pokémon data
        query = """
            SELECT * FROM users_pokemon 
            WHERE userid = $1 AND pokemon_id = $2
        """
        async with self.bot.db.pool.acquire() as conn:
            pokemon_data = await conn.fetchrow(query, user_id, pokemon_id)

        if not pokemon_data:
            await ctx.send(f"No Pokémon found with ID {pokemon_id}.")
            return

        view = self.InfoView(self.bot, user_id, pokemon_id)
        await view.update_embed(ctx, pokemon_id)  # ✅ Display Pokémon info


async def setup(bot):
    await bot.add_cog(PokemonInfo(bot))

