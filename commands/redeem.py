import discord
from discord.ext import commands
from utils.pokemon_utils import get_base_stats  # Import to fetch base stats
import os
import json
from utils.susp_check import is_not_suspended
import aiohttp
import tempfile
import random

# Load aliases from alias.json
ALIASES_FILE = os.path.join("functions", "alias.json")
with open(ALIASES_FILE, "r", encoding="utf-8") as f:
    ALIASES = json.load(f)

with open("number.json", "r", encoding="utf-8") as f:
    IMAGE_COUNTS = json.load(f)

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/pokedia/images/main/final"

class RedeemCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Use bot.db instead of creating a new instance

    async def download_random_image(self, pokemon_name: str):
        pokemon = pokemon_name.lower().strip()

        max_images = IMAGE_COUNTS.get(pokemon)
        if not max_images:
            return None

        image_number = random.randint(1, max_images)
        url = f"{GITHUB_RAW_BASE}/{pokemon}/{image_number}.png"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.close()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    os.unlink(tmp.name)
                    return None

                with open(tmp.name, "wb") as f:
                    f.write(await resp.read())

        return tmp.name



    @commands.command(aliases=["redeems"])
    @is_not_suspended()
    async def rd(self, ctx):
        """Check user's redeem count."""
        user_id = ctx.author.id

        # Fetch user's redeem count from the database
        user_data = await self.bot.db.fetchrow("SELECT redeems FROM users WHERE userid = $1", user_id)

        if not user_data:
            await ctx.send(f"{ctx.author.mention}, you don't have a redeem record yet!")
            return

        redeems = user_data["redeems"]

        embed = discord.Embed(
            title=f"{ctx.author.name}'s Redeems",
            description=f"**Redeems**: {redeems}\n\n**You can redeemspawn a Pokémon by `!rs <pokemon_name>` or `!redeemspawn <pokemon_name>` and catch it!**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="redeemspawn", aliases=["rs"])
    @is_not_suspended()
    async def rs(self, ctx, *, pokemon_name: str):
        """Redeem a Pokémon and spawn it for the user."""
        user_id = ctx.author.id

        NON_REDEEMABLE_POKEMON = {
            "gifts-vulpix", "cupcake-swirlix", "marsheon", "mawdino",
            "empalade", "mewoxys", "mewlander", "boss-squirtle",
            "balloons-spheal", "waiter-snorlax", "hotchocolate-lotad",
            "chef-teddiursa", "mr-jester",
            "reindeer-manectric", "snowball-pikachu", "lights-amaura", "arctic-snow-zorua",
            "tapu-bael", "aurora-celebi", "christmas-timburr"
        }

        normalized_name = pokemon_name.lower().replace(" ", "-")

        for official_name, aliases in ALIASES.items():
            alias_list = [a.lower().replace(" ", "-") for a in aliases]
            if normalized_name in alias_list:
                pokemon_name = official_name
                normalized_name = official_name.lower().replace(" ", "-")
                break

        if normalized_name in NON_REDEEMABLE_POKEMON:
            await ctx.send("This Pokémon is not redeemable.")
            return

        if normalized_name == "ash-greninja":
            await ctx.send("Nice Try Buddy!")
            return

        user_data = await self.bot.db.fetchrow(
            "SELECT redeems FROM users WHERE userid = $1", user_id
        )

        if not user_data or user_data["redeems"] < 1:
            await ctx.send(f"{ctx.author.mention}, you don't have enough redeems!")
            return

        base_stats = get_base_stats(normalized_name)
        if base_stats is None:
            await ctx.send(f"Error: Could not fetch stats for {normalized_name}.")
            return

        await self.bot.db.execute(
            "UPDATE users SET redeems = redeems - 1 WHERE userid = $1", user_id
        )

        # 🔥 NEW IMAGE SYSTEM (ONLY CHANGE)
        image_path = await self.download_random_image(normalized_name)
        if not image_path:
            await ctx.send("Error: Pokémon image not found.")
            return

        file = discord.File(image_path, filename="pokemon.png")

        channel_id = str(ctx.channel.id)
        self.bot.channel_spawns[channel_id] = {
            "name": normalized_name,
            "base_stats": base_stats,
        }

        embed = discord.Embed(
            title="A Pokémon has been redeemed!",
            description=f"{ctx.author.mention} has redeemed **{pokemon_name.capitalize()}**! Catch it using `!catch <name>`!",
            color=discord.Color.green(),
        )
        embed.set_image(url="attachment://pokemon.png")

        await ctx.send(embed=embed, file=file)

        # 🧹 cleanup
        os.unlink(image_path)


async def setup(bot):
    await bot.add_cog(RedeemCommand(bot))


