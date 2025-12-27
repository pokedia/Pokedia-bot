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


class GiftBox(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def send_reward_error(self, error_text: str):
        channel = self.bot.get_channel(1451324331371139262)
        if channel:
            await channel.send(
                f"⚠️ **Santa Box Reward Error**\n```{error_text}```"
            )

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
        await self.db.execute(
            "UPDATE users SET pokecash = pokecash + $1 WHERE userid = $2",
            amount, int(user_id)
        )

    async def insert_shards(self, user_id, amount):
        await self.db.execute(
            "UPDATE users SET shards = shards + $1 WHERE userid = $2",
            amount, int(user_id)
        )

    async def insert_redeems(self, user_id, amount=1):
        await self.db.execute(
            "UPDATE users SET redeems = redeems + $1 WHERE userid = $2",
            amount, int(user_id)
        )

    @commands.command(name="santa", aliases=["st"])
    async def birthday(self, ctx, action: str, amount: int):
        if action.lower() not in ("open", "o"):
            return

        if amount <= 0:
            await ctx.send("You must open at least **1** Santa Box.")
            return

        if amount > 20:
            await ctx.send("You can only open up to **20** Santa Boxes at a time!")
            return

        user_id = int(ctx.author.id)

        gift_count = await self.db.fetchval(
            "SELECT value FROM inventory WHERE userid = $1 AND item_name = 'Santa Box'",
            user_id
        )

        if gift_count is None or gift_count < amount:
            await ctx.send("You don't have enough Santa Boxes!")
            return

        await self.db.execute(
            "UPDATE inventory SET value = value - $1 WHERE userid = $2 AND item_name = 'Santa Box'",
            amount, user_id
        )

        rewards = []
        reward_types = ["pokecash", "shards", "pokemon", "redeem", "special_pokemon"]
        probabilities = [20, 20, 19, 1, 25]

        for i in range(amount):
            reward = random.choices(reward_types, weights=probabilities)[0]

            try:
                if reward == "pokecash":
                    pokecash = random.randint(1500, 2000)
                    await self.insert_pokecash(user_id, pokecash)
                    rewards.append(f"• 🪙 **{pokecash} Pokecash**")

                elif reward == "shards":
                    shards = random.randint(20, 50)
                    await self.insert_shards(user_id, shards)
                    rewards.append(f"• 💎 **{shards} Shards**")

                elif reward == "pokemon":
                    pokemon_name = fetch_pokemon_name()
                    if not pokemon_name:
                        raise ValueError("fetch_pokemon_name() returned None")

                    user_data = await self.db.fetchrow(
                        "SELECT shiny_hunt, streak FROM users WHERE userid = $1",
                        user_id
                    )

                    shiny_hunt = (user_data["shiny_hunt"] or "").lower()
                    streak = user_data["streak"] or 0

                    pokemon_name_lower = pokemon_name.lower()

                    if pokemon_name_lower == shiny_hunt:
                        shiny_chance = (1 + (streak ** 0.5) / 7) / 250
                    else:
                        shiny_chance = 1 / 250

                    is_shiny = random.random() < shiny_chance

                    level = random.randint(1, 30)
                    iv_percentage = get_random_iv_percentage()
                    base_stats = get_base_stats(pokemon_name)

                    if not base_stats:
                        raise ValueError(f"Base stats not found for {pokemon_name}")

                    stats = generate_stats(base_stats, iv_percentage, level)
                    clean_name = pokemon_name.replace("-", " ")

                    await self.insert_pokemon(
                        user_id, clean_name, level, iv_percentage, stats, is_shiny
                    )

                    emoji = await self.bot.get_cog("Sprites").get_pokemon_emoji(clean_name)

                    rewards.append(
                        f"• {emoji} **✨ {clean_name} • Lvl {level} • IV {iv_percentage}%**"
                        if is_shiny else
                        f"• {emoji} **{clean_name} • Lvl {level} • IV {iv_percentage}%**"
                    )

                elif reward == "redeem":
                    await self.insert_redeems(user_id)
                    rewards.append("• 🎟️ **1 Redeem**")

                elif reward == "special_pokemon":
                    special_pokemon_list = {
                        "Christmas-Timburr": 20,
                        "Reindeer-Manectric": 15,
                        "Snowball-Pikachu": 10,
                        "Arctic-Snow-Zorua": 8,
                        "Lights-Amaura": 5
                    }

                    raw_name = random.choices(
                        list(special_pokemon_list.keys()),
                        weights=list(special_pokemon_list.values())
                    )[0]

                    clean_name = raw_name.replace("-", " ")
                    level = random.randint(1, 40)
                    iv_percentage = get_random_iv_percentage()
                    base_stats = get_base_stats(raw_name)

                    if not base_stats:
                        raise ValueError(f"Base stats not found for {raw_name}")

                    stats = generate_stats(base_stats, iv_percentage, level)
                    is_shiny = random.randint(1, 300) == 1

                    await self.insert_pokemon(
                        user_id, clean_name, level, iv_percentage, stats, is_shiny
                    )

                    emoji = await self.bot.get_cog("Sprites").get_pokemon_emoji(clean_name)

                    rewards.append(
                        f"• {emoji} **✨ {clean_name} • Lvl {level} • IV {iv_percentage}%**"
                        if is_shiny else
                        f"• {emoji} **{clean_name} • Lvl {level} • IV {iv_percentage}%**"
                    )

            except Exception as e:
                error_msg = (
                    f"User ID: {user_id}\n"
                    f"Reward Index: {i + 1}\n"
                    f"Reward Type: {reward}\n"
                    f"Error: {repr(e)}"
                )
                logging.error(error_msg)
                await self.send_reward_error(error_msg)

        if not rewards:
            rewards.append("No rewards could be processed.")

        embed = discord.Embed(
            title=f"You opened {amount} Santa Box{'es' if amount > 1 else ''}!",
            description="\n".join(rewards),
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GiftBox(bot, bot.db))


