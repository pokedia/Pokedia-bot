import random
import discord
from discord.ext import commands
from utils.pokemon_utils import generate_stats, get_base_stats
from functions.fetch_pokemon import fetch_pokemon_name
import json
import logging

logging.basicConfig(level=logging.INFO)


def get_random_iv_percentage():
    with open("iv_rarity.json", "r") as file:
        iv_data = json.load(file)

    iv_percentages = [entry["IV Percentage"] for entry in iv_data.values()]
    probabilities = [entry["Probability"] for entry in iv_data.values()]
    return random.choices(iv_percentages, weights=probabilities)[0]


class SnowBox(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def insert_pokemon(self, user_id, pokemon_name, level, iv_percentage, stats, is_shiny):
        max_xp = 275 + (level - 1) * 25

        await self.db.execute(
            """
            INSERT INTO users_pokemon (
                userid, pokemon_id, xp, pokemon_name, level, total_iv_percent,
                hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                hp, attack, defense, spatk, spdef, speed,
                shiny, fusionable, selected, favorite, caught, unique_id, max_xp, nickname
            )
            VALUES (
                $1,
                (SELECT COALESCE(MAX(pokemon_id), 0) + 1 FROM users_pokemon WHERE userid=$1),
                0, $2, $3, $4,
                $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16,
                $17, FALSE, FALSE, FALSE, FALSE,
                gen_random_uuid(), $18, ''
            )
            """,
            int(user_id), pokemon_name, level, iv_percentage,
            stats['hp']['iv'], stats['attack']['iv'], stats['defense']['iv'],
            stats['special-attack']['iv'], stats['special-defense']['iv'], stats['speed']['iv'],
            stats['hp']['value'], stats['attack']['value'], stats['defense']['value'],
            stats['special-attack']['value'], stats['special-defense']['value'], stats['speed']['value'],
            is_shiny, max_xp
        )

    async def insert_pokecash(self, user_id, amount):
        await self.db.execute("UPDATE users SET pokecash = pokecash + $1 WHERE userid = $2", amount, int(user_id))

    async def insert_shards(self, user_id, amount):
        await self.db.execute("UPDATE users SET shards = shards + $1 WHERE userid = $2", amount, int(user_id))

    async def insert_redeems(self, user_id, amount=1):
        await self.db.execute("UPDATE users SET redeems = redeems + $1 WHERE userid = $2", amount, int(user_id))

    @commands.command(name="snow", aliases=["sn"])
    async def birthday(self, ctx, action: str, amount: int):
        if action.lower() not in ("open", "o"):
            return

        if amount <= 0:
            await ctx.send("You must open at least **1** Snow Box.")
            return

        if amount > 20:
            await ctx.send("You can only open up to **20** Snow Boxes at a time!")
            return

        user_id = int(ctx.author.id)
        gift_count = await self.db.fetchval(
            "SELECT value FROM inventory WHERE userid = $1 AND item_name = 'Snow Box'", user_id
        )
        if gift_count is None or gift_count < amount:
            await ctx.send("You don't have enough Santa Boxes!")
            return

        # Safe to subtract only after validation
        await self.db.execute(
            "UPDATE inventory SET value = value - $1 WHERE userid = $2 AND item_name = 'Snow Box'",
            amount, user_id
        )

        rewards = []
        reward_types = ["special_pokemon"]
        probabilities = [100]

        for i in range(amount):
            reward = random.choices(reward_types, weights=probabilities)[0]
            logging.info(f"Reward {i + 1}: {reward}")

            try:
                if reward == "pokecash":
                    pokecash = random.randint(1500, 2000)
                    await self.insert_pokecash(user_id, pokecash)
                    rewards.append(f"\u2022 🪙 **{pokecash} Pokecash**")

                elif reward == "shards":
                    shards = random.randint(20, 50)
                    await self.insert_shards(user_id, shards)
                    rewards.append(f"\u2022 💎 **{shards} Shards**")

                elif reward == "pokemon":
                    pokemon_name = fetch_pokemon_name()
                    # Fetch shiny_hunt and streak from the user's table using the provided query
                    user_data = await self.bot.db.fetchrow(
                        "SELECT shiny_hunt, streak FROM users WHERE userid = $1", user_id
                    )

                    # Ensure user_data is valid
                    if not user_data:
                        logging.warning(f"Skipping: User data for {user_id} not found.")
                        continue

                    # Get shiny_hunt and streak values from user data
                    shiny_hunt = user_data.get("shiny_hunt", "").lower()  # Ensure it's lowercase
                    streak = user_data.get("streak", 0)  # Get streak value

                    # Fetch the pokemon_name in lowercase for comparison
                    pokemon_name_lower = pokemon_name.lower()

                    # Set the shiny chance based on the shiny_hunt column and streak value
                    if pokemon_name_lower == shiny_hunt:
                        # Adjust shiny chance based on streak value
                        shiny_chance = (1 + (streak ** 0.5) / 7) / 250
                    else:
                        shiny_chance = 1 / 250  # Regular shiny chance if not matching the shiny_hunt

                    # Determine if the Pokémon is shiny based on the calculated chance
                    is_shiny = random.randint(1, 250) <= (shiny_chance * 250)  # Compare with shiny chance

                    # Continue with the Pokémon creation process
                    if not pokemon_name:
                        logging.warning(f"Skipping: fetch_pokemon_name() returned None")
                        continue

                    level = random.randint(1, 30)
                    iv_percentage = get_random_iv_percentage()
                    base_stats = get_base_stats(pokemon_name)
                    if not base_stats:
                        logging.warning(f"Skipping: get_base_stats({pokemon_name}) returned None")
                        continue

                    stats = generate_stats(base_stats, iv_percentage, level)
                    await self.insert_pokemon(user_id, pokemon_name.replace("-", " "), level, iv_percentage, stats,
                                              is_shiny)

                    # Add the Pokémon reward message
                    emoji = await self.bot.get_cog("Sprites").get_pokemon_emoji(pokemon_name.replace("-", " "))
                    rewards.append(
                        f"\u2022 {emoji} **✨ {pokemon_name.replace('-', ' ')} • Lvl {level} • IV {iv_percentage}%**"
                        if is_shiny else
                        f"\u2022 {emoji} **{pokemon_name.replace('-', ' ')} • Lvl {level} • IV {iv_percentage}%**"
                    )


                elif reward == "redeem":
                    await self.insert_redeems(user_id)
                    rewards.append("\u2022 🎟️ **1 Redeem**")

                elif reward == "special_pokemon":
                    special_pokemon_list = {
                        "Tapu-Bael": 50,
                        "Aurora-Celebi": 50,
                    }

                    special_pokemon_raw = random.choices(
                        list(special_pokemon_list.keys()), weights=list(special_pokemon_list.values()), k=1
                    )[0]

                    special_pokemon = special_pokemon_raw.replace("-", " ")
                    level = random.randint(1, 40)
                    iv_percentage = get_random_iv_percentage()
                    base_stats = get_base_stats(special_pokemon_raw)


                    if not base_stats:
                        logging.warning(f"Skipping: get_base_stats({special_pokemon}) returned None")
                        continue

                    stats = generate_stats(base_stats, iv_percentage, level)
                    is_shiny = random.randint(1, 300) == 1
                    await self.insert_pokemon(user_id, special_pokemon, level, iv_percentage, stats, is_shiny)

                    emoji = await self.bot.get_cog("Sprites").get_pokemon_emoji(special_pokemon)
                    rewards.append(
                        f"\u2022 {emoji} **✨ {special_pokemon} • Lvl {level} • IV {iv_percentage}%**"
                        if is_shiny else
                        f"\u2022 {emoji} **{special_pokemon} • Lvl {level} • IV {iv_percentage}%**"
                    )

            except Exception as e:
                logging.error(f"Error processing reward {reward}: {e}")

        if not rewards:
            rewards.append("No rewards could be processed.")

        embed = discord.Embed(
            title=f"You opened {amount} Snow Box{'es' if amount > 1 else ''}!",
            color=discord.Color.gold(),
            description="\n".join(rewards)
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SnowBox(bot, bot.db))
