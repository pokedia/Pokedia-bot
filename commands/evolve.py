import discord
from discord.ext import commands
import json
from utils.pokemon_utils import get_base_stats, generate_stats
import re
from utils.susp_check import is_not_suspended


def normalize_pokemon_name(name: str) -> str:
    name = name.lower().replace(" ", "-")
    name = re.sub(r"[^a-z0-9\-]", "", name)
    return name

class PokemonEvolve(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("pokemon_evolution.json", "r") as f:
            self.evolution_data = json.load(f)

    @commands.command(aliases=["evl"])
    @is_not_suspended()
    async def evolve(self, ctx, pokemon_id: int):
        """Manually evolve a Pokémon if it meets the level requirement."""
        user_id = ctx.author.id

        async with self.bot.db.pool.acquire() as conn:
            pokemon = await conn.fetchrow("""
                SELECT * FROM users_pokemon 
                WHERE userid = $1 AND pokemon_id = $2
            """, user_id, pokemon_id)

            if not pokemon:
                return await ctx.send("Invalid Pokémon ID.")

            current_name = pokemon["pokemon_name"]
            current_level = pokemon["level"]

            # Check if this Pokémon can evolve
            if current_name not in self.evolution_data:
                return await ctx.send(f"**{current_name}** has no evolutions.")

            # Look for a valid level-based evolution
            evolution_triggered = False
            for evolution in self.evolution_data[current_name]:
                if evolution["Level"] is not None and current_level >= evolution["Level"]:
                    new_name = evolution["To"]
                    evolution_triggered = True
                    break

            if not evolution_triggered:
                return await ctx.send(
                    f"Your **{current_name}** needs to be at least **Level {evolution['Level']}** to evolve!"
                )

            # Generate new stats using the evolved Pokémon's base stats
            base_stats = get_base_stats(new_name.replace(" ", "-"))
            new_stats = generate_stats(base_stats, pokemon["total_iv_percent"], current_level)

            await conn.execute("""
                UPDATE users_pokemon 
                SET pokemon_name = $1,
                    hp = $2, attack = $3, defense = $4, 
                    spatk = $5, spdef = $6, speed = $7
                WHERE userid = $8 AND pokemon_id = $9
            """, new_name,
                new_stats["hp"]["value"], new_stats["attack"]["value"], new_stats["defense"]["value"],
                new_stats["special-attack"]["value"], new_stats["special-defense"]["value"],
                new_stats["speed"]["value"],
                user_id, pokemon_id
            )

            # Send evolution embed
            embed = discord.Embed(
                title="✨ Evolution Successful! ✨",
                description=f"Your **{current_name}** evolved into a **{new_name}**!",
                color=discord.Color.green()
            )
            image_name = normalize_pokemon_name(new_name)
            embed.set_thumbnail(
                url=f"https://raw.githubusercontent.com/pokedia/images/main/pokemon_images/{image_name}.png")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(PokemonEvolve(bot))


