import random
import uuid
from discord.ext import commands
from utils.pokemon_utils import generate_stats, get_base_stats, is_valid_starter
from database import db  # Import your database instance
from utils.susp_check import is_not_suspended

import logging
logging.basicConfig(level=logging.DEBUG)

def load_iv_rarity():
    import json
    with open('iv_rarity.json', 'r') as f:
        iv_rarity_data = json.load(f)

    iv_probabilities = []
    cumulative_prob = 0.0
    for iv, data in iv_rarity_data.items():
        cumulative_prob += data['Probability']
        iv_probabilities.append((iv, data['IV Percentage'], cumulative_prob))

    return iv_probabilities

def get_random_iv(iv_probabilities):
    rand = random.random()
    for iv, iv_percentage, cumulative_prob in iv_probabilities:
        if rand <= cumulative_prob:
            return int(iv_percentage)
    return int(iv_probabilities[-1][1])

class PickStarter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.iv_probabilities = load_iv_rarity()

    @commands.command()
    @is_not_suspended()
    async def pick(self, ctx, pokemon_name: str):
        logging.debug(f"🔥 DEBUG: pick() called by {ctx.author.id} for {pokemon_name}")

        await db.connect()
        user_id = ctx.author.id
        pokemon_name = pokemon_name.lower()

        async with db.pool.acquire() as conn:
            logging.debug(f"🔥 DEBUG: Acquired database connection for user {user_id}")

            try:
                user = await db.get_user(user_id)
                logging.debug(f"🔥 DEBUG: get_user() returned for {user_id}: {user}")

                existing_pokemon = await conn.fetchval(
                    "SELECT COUNT(*) FROM users_pokemon WHERE userid = $1", user_id
                )
                logging.debug(f"🔥 DEBUG: Existing Pokémon count for {user_id} = {existing_pokemon}")

                if existing_pokemon > 0:
                    await ctx.send(f"{ctx.author.mention}, you have already picked your starter!")
                    return

                if not is_valid_starter(pokemon_name):
                    await ctx.send(f"{ctx.author.mention}, that is not a valid starter Pokémon!")
                    return

                base_stats = get_base_stats(pokemon_name)
                if not base_stats:
                    await ctx.send(f"{ctx.author.mention}, that is not a valid Pokémon!")
                    return

                iv_percentage = get_random_iv(self.iv_probabilities)
                stats = generate_stats(base_stats, iv_percentage, level=1)

                logging.debug(f"🔥 DEBUG: Generated stats for {pokemon_name.capitalize()} - {stats}")

                is_shiny = random.randint(1, 4096) == 1
                xp = 0
                unique_id = str(uuid.uuid4())  # UUID for unique identifier
                pokemon_id = 1  # Placeholder, adjust based on your system
                max_xp = 225  # ✅ Always set max_xp to 225

                async with conn.transaction():  # ✅ Ensure transaction commits
                    await conn.execute(
                        """
                        INSERT INTO users_pokemon (
                            userid, unique_id, pokemon_id, pokemon_name, level, xp, max_xp,
                            total_iv_percent, hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                            hp, attack, defense, spatk, spdef, speed,
                            shiny, fusionable, selected, favorite, caught
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7,
                            $8, $9, $10, $11, $12, $13, $14,
                            $15, $16, $17, $18, $19, $20,
                            $21, $22, $23, $24, $25
                        )
                        """,
                        user_id, unique_id, pokemon_id, pokemon_name.capitalize(), 1, xp, max_xp,
                        stats['total_iv'], stats['hp']['iv'], stats['attack']['iv'], stats['defense']['iv'],
                        stats['special-attack']['iv'], stats['special-defense']['iv'], stats['speed']['iv'],
                        stats['hp']['value'], stats['attack']['value'], stats['defense']['value'],
                        stats['special-attack']['value'], stats['special-defense']['value'], stats['speed']['value'],
                        is_shiny, False, True, False, True
                    )

                logging.debug(f"✅ DEBUG: Pokémon {pokemon_name.capitalize()} saved successfully for user {user_id}")

                await ctx.send(
                    f"🎉 Congratulations! {ctx.author.mention}, you started your journey with a Level 1 {pokemon_name.capitalize()} ({iv_percentage}% IV)!"
                )

            except Exception as e:
                logging.error(f"❌ ERROR in pick command: {e}")
                await ctx.send("An error occurred while picking your Pokémon. Please try again.")

async def setup(bot):
    await bot.add_cog(PickStarter(bot))
