import discord
import random
import json
from discord.ext import commands
from utils.pokemon_utils import get_base_stats, generate_stats  # Import utility functions
from utils.susp_check import is_not_suspended


class PokemonSelect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_counter = {}  # Tracks messages per user
        with open("pokemon_evolution.json", "r") as f:
            self.evolution_data = json.load(f)  # Load evolution data

    @commands.command(aliases=["s"])
    @is_not_suspended()
    async def select(self, ctx, pokemon_id: int):
        """Select a Pokémon as the active Pokémon."""

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot select a pokemon while in trade.")
            return

        async with self.bot.db.pool.acquire() as conn:
            async with conn.transaction():
                user_id = ctx.author.id
                await conn.execute("""
                    UPDATE users_pokemon 
                    SET selected = FALSE 
                    WHERE userid = $1 AND selected = TRUE""", user_id)

                updated_rows = await conn.execute("""
                    UPDATE users_pokemon 
                    SET selected = TRUE 
                    WHERE userid = $1 AND pokemon_id = $2""", user_id, pokemon_id)

                if updated_rows == "UPDATE 0":
                    return await ctx.send("Invalid Pokémon ID.")

        await ctx.send("Your Pokémon has been selected!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = message.author.id
        async with self.bot.db.pool.acquire() as conn:
            selected_pokemon = await conn.fetchrow("""
                SELECT * FROM users_pokemon WHERE userid = $1 AND selected = TRUE""", user_id)

            if not selected_pokemon:
                return  # No active Pokémon

            self.message_counter[user_id] = self.message_counter.get(user_id, 0) + 1
            if self.message_counter[user_id] % 4 != 0:
                return  # Only give XP every 4 messages

            current_level = selected_pokemon["level"]
            current_xp = selected_pokemon["xp"]
            max_xp = selected_pokemon["max_xp"]
            xp_gain = random.randint(10, 40)

            # 🧠 At level 100 and max XP — stop gaining XP
            if current_level >= 100 and current_xp >= max_xp:
                return

            new_xp = current_xp + xp_gain

            # 🧱 Cap XP at max_xp if already level 100
            if current_level >= 100:
                if new_xp > max_xp:
                    new_xp = max_xp

                await conn.execute("""
                    UPDATE users_pokemon 
                    SET xp = $1 
                    WHERE userid = $2 AND pokemon_id = $3""",
                                   new_xp, user_id, selected_pokemon["pokemon_id"]
                                   )
                return

            # 🔼 Leveling up logic (below level 100)
            if new_xp >= max_xp:
                new_level = current_level + 1
                new_xp = 0
                max_xp += 25
                evolved = False
                new_pokemon_name = selected_pokemon["pokemon_name"]

                if new_pokemon_name in self.evolution_data:
                    for evolution in self.evolution_data[new_pokemon_name]:
                        if evolution["Level"] is not None and new_level >= evolution["Level"]:
                            new_pokemon_name = evolution["To"]
                            evolved = True
                            break

                base_stats = get_base_stats(new_pokemon_name.replace(" ", "-"))
                new_stats = generate_stats(base_stats, selected_pokemon["total_iv_percent"], new_level)

                await conn.execute("""
                    UPDATE users_pokemon 
                    SET level = $1, xp = $2, max_xp = $3, pokemon_name = $4,
                        hp = $5, attack = $6, defense = $7, spatk = $8, spdef = $9, speed = $10
                    WHERE userid = $11 AND pokemon_id = $12""",
                                   new_level, new_xp, max_xp, new_pokemon_name,
                                   new_stats["hp"]["value"], new_stats["attack"]["value"],
                                   new_stats["defense"]["value"], new_stats["special-attack"]["value"],
                                   new_stats["special-defense"]["value"], new_stats["speed"]["value"],
                                   user_id, selected_pokemon["pokemon_id"]
                                   )

                if evolved:
                    embed = discord.Embed(
                        title="✨ Evolution Alert! ✨",
                        description=f"**OH.. Your {selected_pokemon['pokemon_name']} is evolving..**\n"
                                    f"It evolved into a **{new_pokemon_name}**!",
                        color=discord.Color.gold()
                    )
                    embed.set_thumbnail(
                        url=f"https://github.com/pokedia/images/blob/main/pokemon_images/{new_pokemon_name}.png?raw=true")
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(
                        f"🎉 {message.author.mention} Your **{selected_pokemon['pokemon_name']}** leveled up to **Level {new_level}**!"
                    )
            else:
                await conn.execute("""
                    UPDATE users_pokemon 
                    SET xp = $1 
                    WHERE userid = $2 AND pokemon_id = $3""",
                                   new_xp, user_id, selected_pokemon["pokemon_id"]
                                   )

async def setup(bot):
    await bot.add_cog(PokemonSelect(bot))
