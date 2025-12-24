import discord
from discord.ext import commands
import uuid
from utils.pokemon_utils import generate_stats, get_base_stats

ALLOWED_USER_IDS = {760720549092917248, 832484278197420052, 688983124868202496}

class RegenerateStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rgs")
    async def regenerate_stats(self, ctx, unique_id: str):
        if ctx.author.id not in ALLOWED_USER_IDS:
            return await ctx.send("❌ You do not have permission to use this command.")

        try:
            uid = uuid.UUID(unique_id)
        except ValueError:
            return await ctx.send("❌ Invalid UUID format.")

        async with self.bot.db.pool.acquire() as conn:
            pokemon = await conn.fetchrow(
                "SELECT * FROM users_pokemon WHERE unique_id = $1",
                str(uid)
            )
            if not pokemon:
                return await ctx.send("❌ No Pokémon found with that unique_id.")

            stored_total_iv_percent = pokemon["total_iv_percent"]
            level = pokemon["level"]
            base_stats = await self.get_base_stats_for_pokemon(pokemon["pokemon_name"])

            iv_sum = (
                pokemon["hp_iv"] +
                pokemon["attack_iv"] +
                pokemon["defense_iv"] +
                pokemon["spatk_iv"] +
                pokemon["spdef_iv"] +
                pokemon["speed_iv"]
            )
            total_possible_iv = 31 * 6
            avg_iv_percent = round((iv_sum / total_possible_iv) * 100, 2)

            capped_level = min(level, 100)

            if abs(avg_iv_percent - stored_total_iv_percent) > 0.01:
                new_stats = generate_stats(base_stats, stored_total_iv_percent, capped_level)

                await conn.execute(
                    """
                    UPDATE users_pokemon SET
                        hp = $1,
                        attack = $2,
                        defense = $3,
                        spatk = $4,
                        spdef = $5,
                        speed = $6,
                        hp_iv = $7,
                        attack_iv = $8,
                        defense_iv = $9,
                        spatk_iv = $10,
                        spdef_iv = $11,
                        speed_iv = $12,
                        total_iv_percent = $13,
                        level = $14
                    WHERE unique_id = $15
                    """,
                    new_stats["hp"]["value"],
                    new_stats["attack"]["value"],
                    new_stats["defense"]["value"],
                    new_stats["special-attack"]["value"],
                    new_stats["special-defense"]["value"],
                    new_stats["speed"]["value"],
                    new_stats["hp"]["iv"],
                    new_stats["attack"]["iv"],
                    new_stats["defense"]["iv"],
                    new_stats["special-attack"]["iv"],
                    new_stats["special-defense"]["iv"],
                    new_stats["speed"]["iv"],
                    new_stats["total_iv"],
                    capped_level,
                    str(uid)
                )
                await ctx.send(f"✅ Pokémon IVs and stats regenerated for unique_id `{unique_id}` to match stored total IV %.")
                return

            if level > 100:
                ivs = {
                    "hp": pokemon["hp_iv"],
                    "attack": pokemon["attack_iv"],
                    "defense": pokemon["defense_iv"],
                    "special-attack": pokemon["spatk_iv"],
                    "special-defense": pokemon["spdef_iv"],
                    "speed": pokemon["speed_iv"],
                }

                recalculated_stats = {}
                for stat in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]:
                    base = base_stats[stat]
                    iv = ivs[stat]
                    if stat == "hp":
                        val = ((2 * base + iv) * capped_level) // 100 + capped_level + 10
                    else:
                        val = ((2 * base + iv) * capped_level) // 100 + 5
                    recalculated_stats[stat] = val

                await conn.execute(
                    """
                    UPDATE users_pokemon SET
                        hp = $1,
                        attack = $2,
                        defense = $3,
                        spatk = $4,
                        spdef = $5,
                        speed = $6,
                        level = $7,
                        max_xp = 2750
                    WHERE unique_id = $8
                    """,
                    recalculated_stats["hp"],
                    recalculated_stats["attack"],
                    recalculated_stats["defense"],
                    recalculated_stats["special-attack"],
                    recalculated_stats["special-defense"],
                    recalculated_stats["speed"],
                    capped_level,
                    str(uid)
                )
                await ctx.send(
                    f"✅ Pokémon stats recalculated for level 100 for unique_id `{unique_id}`, max_xp set to 2750.")
                return

            await ctx.send("ℹ️ No update needed — IVs and level are already consistent.")

    async def get_base_stats_for_pokemon(self, pokemon_name: str) -> dict:
        return get_base_stats(pokemon_name)  # no modification, direct call

async def setup(bot):
    await bot.add_cog(RegenerateStats(bot))
