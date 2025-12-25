import random
import json
import discord
from discord.ext import commands
import asyncio

from database import Database
from utils.pokemon_utils import generate_stats
from utils.susp_check import is_not_suspended


def load_iv_rarity():
    with open('iv_rarity.json', 'r') as f:
        iv_rarity_data = json.load(f)

    iv_probabilities = []
    cumulative_prob = 0.0
    for iv, data in iv_rarity_data.items():
        cumulative_prob += data['Probability']
        iv_probabilities.append((iv, data['IV Percentage'], cumulative_prob))
    return iv_probabilities


def load_aliases():
    with open("functions/alias.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_random_iv(iv_probabilities):
    rand = random.random()
    for iv, iv_percentage, cumulative_prob in iv_probabilities:
        if rand <= cumulative_prob:
            return iv_percentage
    return iv_probabilities[-1][1]


class CatchCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alias_data = load_aliases()
        self.iv_probabilities = load_iv_rarity()

        if not hasattr(self.bot, "channel_spawns"):
            self.bot.channel_spawns = {}

        self.catch_locks = {}  # channel_id -> asyncio.Lock

    @commands.command(name="catch", aliases=["c"])
    @is_not_suspended()
    async def catch(self, ctx, *, pokemon_name: str):
        user_id = ctx.author.id
        channel_id = str(ctx.channel.id)

        if channel_id not in self.catch_locks:
            self.catch_locks[channel_id] = asyncio.Lock()

        async with self.catch_locks[channel_id]:

            # Journey check
            pokemon_count = await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM users_pokemon WHERE userid = $1",
                user_id
            )
            if pokemon_count == 0:
                await ctx.send("Kindly start your journey first.")
                return

            # Spawn check
            if channel_id not in self.bot.channel_spawns:
                await ctx.send("There is no Pokémon to catch in this channel right now!")
                return

            spawn_data = self.bot.channel_spawns[channel_id]
            stored_name = spawn_data["name"].replace("-", " ").title()

            # Normalize correct names
            stored_name_normalized = spawn_data["name"].replace("-", " ").lower()
            correct_names = {spawn_data["name"].lower(), stored_name_normalized}

            # Aliases support
            for key, aliases in self.alias_data.items():
                alias_set = {a.lower() for a in aliases}
                if stored_name_normalized in alias_set:
                    correct_names.add(key.lower())
                    correct_names.update(alias_set)
                    break

            if pokemon_name.lower() not in correct_names:
                await ctx.send("That's not the correct Pokémon! Guess the Pokémon correctly!")
                return

            # Generate Pokémon
            level = random.randint(1, 40)
            iv_percentage = get_random_iv(self.iv_probabilities)
            stats = generate_stats(spawn_data["base_stats"], iv_percentage, level)

            # Shiny logic
            user_data = await self.bot.db.fetchrow(
                "SELECT shiny_hunt, streak, shinycharm FROM users WHERE userid = $1",
                user_id
            )

            shiny_hunt_target = user_data["shiny_hunt"] if user_data else None
            streak = user_data["streak"] if user_data else 0
            has_shiny_charm = user_data["shinycharm"] if user_data else False

            shiny_denominator = 3276 if has_shiny_charm else 4096

            if shiny_hunt_target and shiny_hunt_target.lower() == stored_name.lower():
                shiny_chance = (1 + (streak ** 0.5) / 7) / shiny_denominator
            else:
                shiny_chance = 1 / shiny_denominator

            is_shiny = random.random() <= shiny_chance

            # Stats unpack
            hp, hp_iv = stats['hp']['value'], stats['hp']['iv']
            attack, attack_iv = stats['attack']['value'], stats['attack']['iv']
            defense, defense_iv = stats['defense']['value'], stats['defense']['iv']
            spatk, spatk_iv = stats['special-attack']['value'], stats['special-attack']['iv']
            spdef, spdef_iv = stats['special-defense']['value'], stats['special-defense']['iv']
            speed, speed_iv = stats['speed']['value'], stats['speed']['iv']

            max_xp = 275 + (level - 1) * 25

            # Insert Pokémon
            await self.bot.db.execute("""
                INSERT INTO users_pokemon (
                    userid, pokemon_id, xp, pokemon_name, level, total_iv_percent,
                    hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                    hp, attack, defense, spatk, spdef, speed,
                    shiny, max_xp, caught
                ) VALUES (
                    $1,
                    (SELECT COALESCE(MAX(pokemon_id), 0) + 1 FROM users_pokemon WHERE userid = $1),
                    0, $2, $3, $4,
                    $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16,
                    $17, $18, true
                )
            """,
            user_id, stored_name, level, iv_percentage,
            hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
            hp, attack, defense, spatk, spdef, speed,
            is_shiny, max_xp)

            # 🎄 Snow Coin drop (1 in 8 chance)
            snow_coin_dropped = random.randint(1, 5) == 1


            if snow_coin_dropped:
                await self.bot.db.execute(
                    """
                    INSERT INTO inventory (userid, item_name, value)
                    VALUES ($1, 'Snow Coin', 1)
                    ON CONFLICT (userid, item_name)
                    DO UPDATE SET value = inventory.value + 1
                    """,
                    user_id
                )

            # Check if star is active
            star_active = await self.bot.db.fetchval(
                "SELECT star FROM users WHERE userid = $1",
                user_id
            )

            star_dropped = False  # default value

            if star_active:
                star_dropped = random.randint(1, 3) == 1

            if star_dropped:
                await self.bot.db.execute(
                    """
                    INSERT INTO inventory (userid, item_name, value)
                    VALUES ($1, 'Decor Box', 1)
                    ON CONFLICT (userid, item_name)
                    DO UPDATE SET value = inventory.value + 1
                    """,
                    user_id
                )

            # Shiny streak handling
            streak_footer = ""
            if shiny_hunt_target and shiny_hunt_target.lower() == stored_name.lower():
                if is_shiny:
                    await self.bot.db.execute(
                        "UPDATE users SET streak = 0 WHERE userid = $1",
                        user_id
                    )
                    streak_footer = "\n\n✨ **Shiny streak reset!** ✨"
                else:
                    streak += 1
                    await self.bot.db.execute(
                        "UPDATE users SET streak = $1 WHERE userid = $2",
                        streak, user_id
                    )
                    streak_footer = f"\n\n+1 shiny streak! ({streak})"

            shiny_text = "\n\n✨✨✨...It Looks Different🤔" if is_shiny else ""

            snow_coin_text = "\n\n❄️ You found a **Snow Coin**!" if snow_coin_dropped else ""

            Star_text = "\n\n📦🌟 You Found a **Decor Box** in the Wild!" if star_dropped else ""


            # Remove spawn
            del self.bot.channel_spawns[channel_id]

            # Quest update
            dq_cog = self.bot.get_cog("DailyQuests")
            if dq_cog:
                await dq_cog.update_daily_quest_progress(user_id, stored_name.lower())

            await ctx.send(
                f"🎉 Congratulations {ctx.author.mention}!"
                f"You caught a **Level {level} {stored_name}** with **{iv_percentage}% IV**!"
                f"{snow_coin_text}{Star_text}{streak_footer}{shiny_text}"
            )


async def setup(bot):
    await bot.add_cog(CatchCommand(bot))

