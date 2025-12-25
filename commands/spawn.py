import random
import discord
from discord.ext import commands
import json
import os
import aiohttp
import tempfile

from utils.pokemon_utils import get_base_stats
from functions.fetch_pokemon import fetch_pokemon_name

with open("number.json", "r", encoding="utf-8") as f:
    IMAGE_COUNTS = json.load(f)

ASH_JSON = "ash.json"
ASH_GRENINJA_CHANNEL = 1345838313088618589
ASH_GRENINJA_LIMIT = 5_000_000

# GitHub raw base
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/pokedia/images/main/final"

# Set this to the MAX images any Pokémon folder has
MAX_IMAGES_PER_POKEMON = 20


class SpawnCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_counts = {}
        self.bot.channel_spawns = {}
        self.redirect_file = "redirect_spawns.json"
        self.redirect_spawns = self.load_redirects()

    # ---------------- REDIRECT ----------------

    def load_redirects(self):
        if os.path.exists(self.redirect_file):
            with open(self.redirect_file, "r") as f:
                return json.load(f)
        return {}

    def save_redirects(self):
        with open(self.redirect_file, "w") as f:
            json.dump(self.redirect_spawns, f, indent=4)

    @commands.command(name="redirect_spawn", aliases=["rds"])
    @commands.has_permissions(administrator=True)
    async def redirect_spawn(self, ctx, *channels: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        self.redirect_spawns[guild_id] = [str(c.id) for c in channels]
        self.save_redirects()
        await ctx.send(
            f"Redirected spawns to: {', '.join(c.mention for c in channels)}"
        )

    # ---------------- IMAGE LOGIC (SIMPLE & WORKING) ----------------

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

    async def send_spawn(self, channel, pokemon_name, color, title):
        temp_path = await self.download_random_image(pokemon_name)

        if not temp_path:
            await channel.send("⚠️ Pokémon image not found.")
            return

        file = discord.File(temp_path, filename="pokemon.png")

        embed = discord.Embed(
            title=title,
            description="Guess the Pokémon and catch it by !catch <name>",
            color=color,
        )
        embed.set_image(url="attachment://pokemon.png")

        await channel.send(embed=embed, file=file)
        os.unlink(temp_path)

    # ---------------- ASH GRENINJA ----------------

    # ---------------- NORMAL SPAWNS ----------------

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id)

        self.message_counts[channel_id] = self.message_counts.get(channel_id, 0) + 1

        if self.message_counts[channel_id] < 10:
            return

        self.message_counts[channel_id] = 0

        spawn_channels = self.redirect_spawns.get(guild_id, [channel_id])
        spawn_channel_id = random.choice(spawn_channels)
        spawn_channel = self.bot.get_channel(int(spawn_channel_id))

        pokemon_name = fetch_pokemon_name()
        if not pokemon_name:
            return

        base_stats = get_base_stats(pokemon_name)
        if not base_stats:
            return

        self.bot.channel_spawns[spawn_channel_id] = {
            "name": pokemon_name.lower(),
            "base_stats": base_stats,
        }

        await self.send_spawn(
            spawn_channel,
            pokemon_name,
            discord.Color.green(),
            "A wild Pokémon has appeared!",
        )


async def setup(bot):
    await bot.add_cog(SpawnCommand(bot))
