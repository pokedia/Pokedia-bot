import discord
import random
import os
from discord.ext import commands
from utils.pokemon_utils import generate_stats
import uuid
from utils.susp_check import is_not_suspended

FUSION_PAIRS = {
    ("mew", "chandelure"): "Mewlander",
    ("deoxys", "mewtwo"): "Mewoxys",
    ("mewtwo", "deoxys"): "Mewoxys",
    ("chandelure", "mew"): "Mewlander",
    ("marshadow", "eevee"): "Marsheon",
    ("eevee", "marshadow"): "Marsheon",
    ("audino", "mawile"): "Mawdino",
    ("mawile", "audino"): "Mawdino",
    ("empoleon", "gallade"): "Empalade",
    ("empoleon", "gallade"): "Empalade"
}

FUSION_XP_REQUIREMENTS = {
    "Mewlander": 10000,
    "Mawdino": 7500,
    "Marsheon": 10000,
    "Mewoxys": 15000,
    "Empalade": 10000
}

BASE_STATS = {
    "Mawdino": {"hp": 76, "attack": 72, "defense": 86, "special-attack": 58, "special-defense": 70, "speed": 50},
    "Marsheon": {"hp": 72, "attack": 90, "defense": 65, "special-attack": 68, "special-defense": 78, "speed": 90},
    "Empalade": {"hp": 76, "attack": 106, "defense": 76, "special-attack": 88, "special-defense": 108, "speed": 70},
    "Mewoxys": {"hp": 78, "attack": 130, "defense": 70, "special-attack": 152, "special-defense": 70, "speed": 140},
    "Mewlander": {"hp": 80, "attack": 78, "defense": 95, "special-attack": 123, "special-defense": 95, "speed": 90},
}


class Fuse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_fusion = {}
        self.fusion_xp = {}

    async def get_pokemon_emoji(self, name):
        sprite_cog = self.bot.get_cog("Sprites")
        return await sprite_cog.get_pokemon_emoji(name) if sprite_cog else name.lower()

    @commands.command()
    async def fuse(self, ctx, action: str = None, id1: int = None, id2: int = None):
        user_id = ctx.author.id

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot run this command while in trade.")
            return

        async with self.bot.db.pool.acquire() as conn:
            if action is None:
                embed = discord.Embed(title="🥼 **Pokedia Fusion Lab** 🥼", color=discord.Color.blue())
                embed.description = (
                    "Fusion is a scientific process which occurs between two Pokémon in the fusion incubator, only if their DNA has the fusionable trait. "
                    "Fusion Incubators are costly to run and need a DNA Splicer to start the process of Fusion."
                )

                github_base_url = "https://raw.githubusercontent.com/pokedia/images/main/extras/"

                if user_id in self.user_fusion:
                    poke1, poke2, fusion_name = self.user_fusion[user_id]
                    xp_data = self.fusion_xp.get(user_id,
                                                 {"current": 0, "required": FUSION_XP_REQUIREMENTS[fusion_name]})

                    embed.add_field(
                        name="Your Fusing Pokémon",
                        value=f"{xp_data['current']}/{xp_data['required']}\n"
                              f"{'✨' if poke1['shiny'] else ''}**{poke1['pokemon_id']} • {poke1['pokemon_name']} • lvl {poke1['level']} • {poke1['total_iv_percent']}%**\n"
                              f"{'✨' if poke2['shiny'] else ''}**{poke2['pokemon_id']} • {poke2['pokemon_name']} • lvl {poke2['level']} • {poke2['total_iv_percent']}%**",
                        inline=False
                    )

                    image_url = f"{github_base_url}{fusion_name}_lab.png"
                else:
                    embed.add_field(name="Your Fusing Pokémon", value="0/2\nNone", inline=False)
                    embed.add_field(
                        name="Instructions",
                        value="`To add Pokémon for fusion, use !fuse add <ID> <ID> and !fuse start to start the process`",
                        inline=False
                    )
                    image_url = f"{github_base_url}lab.png"

                embed.add_field(
                    name="Corrupted Pokémon",
                    value="Fusion does not have a 100% success rate and sometimes leads to malfunction, resulting in the formation of Corrupted Pokémon.",
                    inline=False
                )

                embed.set_image(url=image_url)
                await ctx.send(embed=embed)

                return


            elif action == "add" and id1 and id2:

                async with conn.transaction():

                    poke1 = await conn.fetchrow("SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                                                user_id, id1)

                    poke2 = await conn.fetchrow("SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                                                user_id, id2)

                    if not poke1 or not poke2:
                        await ctx.send("One or both Pokémon IDs are invalid.")

                        return

                    # ✅ Check if both Pokémon are marked as fusionable

                    if not poke1["fusionable"] or not poke2["fusionable"]:
                        await ctx.send("One or both Pokémon are not fusionable.")

                        return

                    fusion_name = FUSION_PAIRS.get((poke1["pokemon_name"].lower(), poke2["pokemon_name"].lower()))

                    if not fusion_name:
                        await ctx.send("These Pokémon cannot be fused together.")
                        return

                    fusion_name = fusion_name.lower()

                    await conn.execute("DELETE FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2", user_id, id1)

                    await conn.execute("DELETE FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2", user_id, id2)

                    self.user_fusion[user_id] = (poke1, poke2, fusion_name)

                    self.fusion_xp[user_id] = {"current": 0, "required": FUSION_XP_REQUIREMENTS[fusion_name]}

                    await ctx.send(
                        f"Added {'✨' if poke1['shiny'] else ''}**{poke1['pokemon_name']}** and {'✨' if poke2['shiny'] else ''}**{poke2['pokemon_name']}** for fusion!")




            elif action == "remove":

                if user_id in self.fusion_xp and self.fusion_xp[user_id].get("started", False):
                    await ctx.send("The fusion process has already started! You cannot remove your Pokémon now.")

                    return

                if user_id in self.user_fusion:
                    poke1, poke2, _ = self.user_fusion.pop(user_id)

                    async with conn.transaction():
                        await conn.execute(

                            """

                            INSERT INTO users_pokemon 

                            (userid, pokemon_id, xp, max_xp, pokemon_name, level, total_iv_percent, 

                             hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv, 

                             hp, attack, defense, spatk, spdef, speed, shiny, fusionable, 

                             selected, favorite, caught, nickname) 

                            VALUES 

                            ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 

                             $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25),

                            ($1, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, 

                             $38, $39, $40, $41, $42, $43, $44, $45, $46, $47, $48, $49)

                            """,

                            user_id, poke1['pokemon_id'], poke1['xp'], poke1['max_xp'], poke1['pokemon_name'],

                            poke1['level'], poke1['total_iv_percent'], poke1['hp_iv'], poke1['attack_iv'],

                            poke1['defense_iv'], poke1['spatk_iv'], poke1['spdef_iv'], poke1['speed_iv'],

                            poke1['hp'], poke1['attack'], poke1['defense'], poke1['spatk'], poke1['spdef'],
                            poke1['speed'],

                            poke1['shiny'], poke1['fusionable'], poke1['selected'], poke1.get('favorite', False),

                            poke1.get('caught', True), poke1.get('nickname', None),

                            poke2['pokemon_id'], poke2['xp'], poke2['max_xp'], poke2['pokemon_name'],

                            poke2['level'], poke2['total_iv_percent'], poke2['hp_iv'], poke2['attack_iv'],

                            poke2['defense_iv'], poke2['spatk_iv'], poke2['spdef_iv'], poke2['speed_iv'],

                            poke2['hp'], poke2['attack'], poke2['defense'], poke2['spatk'], poke2['spdef'],
                            poke2['speed'],

                            poke2['shiny'], poke2['fusionable'], poke2['selected'], poke2.get('favorite', False),

                            poke2.get('caught', True), poke2.get('nickname', None)

                        )

                    await ctx.send("Fusion process canceled. Pokémon returned to inventory.")




            elif action == "start":

                if user_id not in self.user_fusion:
                    await ctx.send("The Fusion Incubator is Empty..")

                    return

                # Check if user has at least 1 DNA Splicer

                inventory = await conn.fetchrow(

                    "SELECT value FROM inventory WHERE userid = $1 AND item_name = 'DNA Splicer'", user_id

                )

                if not inventory or inventory["value"] < 1:
                    await ctx.send("You don't have a DNA Splicer to start the fusion!")

                    return

                # Deduct 1 DNA Splicer from the user's inventory

                await conn.execute(

                    "UPDATE inventory SET value = value - 1 WHERE userid = $1 AND item_name = 'DNA Splicer'", user_id

                )

                # Fetch the Pokémon being fused

                poke1, poke2, fusion_poke = self.user_fusion[user_id]

                required_xp = FUSION_XP_REQUIREMENTS.get(fusion_poke, 1000)  # Default XP if not found

                # Set fusion XP progress and mark fusion as started

                self.fusion_xp[user_id] = {

                    "current": 0,

                    "required": required_xp,

                    "started": True  # Track if fusion was started

                }

                await ctx.send(
                    f"The fusion process for **{fusion_poke}** has started! You need {required_xp} XP to complete the fusion.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = message.author.id

        # Ensure the user gains XP only if they initiated fusion with !fuse start
        if user_id in self.fusion_xp and self.fusion_xp[user_id].get("started", False):
            xp_data = self.fusion_xp[user_id]
            gained_xp = random.randint(20, 40)
            xp_data["current"] += gained_xp

            if xp_data["current"] >= xp_data["required"]:
                await self.complete_fusion(message)

    async def complete_fusion(self, message):
        user_id = message.author.id
        poke1, poke2, fusion_name = self.user_fusion[user_id]
        avg_level = (poke1["level"] + poke2["level"]) // 2
        avg_iv = (poke1["total_iv_percent"] + poke2["total_iv_percent"]) / 2
        is_shiny = poke1["shiny"] and poke2["shiny"] or (poke1["shiny"] or poke2["shiny"] and random.choice([True, False]))

        stats = generate_stats(BASE_STATS[fusion_name], avg_iv, avg_level)
        async with self.bot.db.pool.acquire() as conn:
            max_xp = 275 + (avg_level - 1) * 25

            async with conn.transaction():
                # Lock all Pokémon rows belonging to this user
                await conn.execute("LOCK TABLE users_pokemon IN SHARE ROW EXCLUSIVE MODE")

                # Now fetch the next sequential pokemon_id safely
                new_pokemon_id = await conn.fetchval(
                    """
                    SELECT COALESCE(MAX(pokemon_id), 0) + 1 
                    FROM users_pokemon 
                    WHERE userid = $1
                    """,
                    user_id
                )

                # Round IV percentage to 2 decimal places
                avg_iv = round((poke1["total_iv_percent"] + poke2["total_iv_percent"]) / 2, 2)

                await conn.execute(
                    """
                    INSERT INTO users_pokemon (userid, pokemon_id, pokemon_name, level, total_iv_percent, 
                                               hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv, 
                                               hp, attack, defense, spatk, spdef, speed, 
                                               max_xp, shiny, fusionable, nickname)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, false, '')
                    """,
                    user_id, new_pokemon_id, fusion_name, avg_level, avg_iv,
                    stats["hp"]["iv"], stats["attack"]["iv"], stats["defense"]["iv"], stats["special-attack"]["iv"],
                    stats["special-defense"]["iv"], stats["speed"]["iv"],
                    stats["hp"]["value"], stats["attack"]["value"], stats["defense"]["value"],
                    stats["special-attack"]["value"], stats["special-defense"]["value"], stats["speed"]["value"],
                    max_xp, is_shiny
                )

        await message.channel.send(f"🎉 {message.author.mention}, your fusion is complete! You received {fusion_name}!")
        del self.user_fusion[user_id]
        del self.fusion_xp[user_id]

async def setup(bot):
    await bot.add_cog(Fuse(bot))
