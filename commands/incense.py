import discord
from discord.ext import commands
import asyncio
from utils.pokemon_utils import get_base_stats
from functions.fetch_pokemon import fetch_pokemon_name
from utils.susp_check import is_not_suspended
import aiohttp
import json
import tempfile
import random
import os
INFINITE_CHANNELS = [
1451324526943142062, 1451324548266856511, 1451324566994682016, 1451324586502127651,
1451324604953002116, 1451324627841192058, 1451324649056108656, 1451324668463284456,
1451324687081799924, 1451324709110026260, 1451324735454580888, 1451324758061879500,
1451324777745744017, 1451324795856748695, 1451324814861275187, 1451324836256419940
]

with open("number.json", "r", encoding="utf-8") as f:
    IMAGE_COUNTS = json.load(f)

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/pokedia/images/main/final"

class IncenseCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.channel_spawns = {}
        self.bot.infinite_incense_channels = set()
        self.bot.loop.create_task(self.monitor_incense())

    async def get_user_shards(self, user_id: int) -> int:
        async with self.bot.db.pool.acquire() as conn:
            result = await conn.fetchval("SELECT shards FROM users WHERE userid = $1", user_id)
            return result if result is not None else 0

    async def deduct_user_shards(self, user_id: int, amount: int):
        async with self.bot.db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET shards = shards - $1 WHERE userid = $2 AND shards >= $1",
                amount, user_id
            )

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
            description="Guess the Pokémon and catch it by `Pokédia#2537catch <name>`",
            color=color,
        )
        embed.set_image(url="attachment://pokemon.png")

        await channel.send(embed=embed, file=file)
        os.unlink(temp_path)

    async def add_incense_to_db(self, server_id: int, channel_id: int, spawn_remaining: int, total_spawns: int,
                                interval: str):
        async with self.bot.db.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO incense (server_id, channel_id, spawn_remaining, total_spawn, interval, paused) VALUES ($1, $2, $3, $4, $5, $6)",
                server_id, channel_id, spawn_remaining, total_spawns, int(interval[:-1]), False  # Convert "10s" to 10
            )

    async def incense_exists_in_db(self, channel_id: int) -> bool:
        async with self.bot.db.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1 FROM incense WHERE channel_id = $1", channel_id)
            return result is not None

    def get_interval_seconds(self, interval: str):
        return int(interval[:-1])

    @commands.command()
    @is_not_suspended()
    async def incense(self, ctx, action: str, duration: str, interval: str):
        # Permission check
        has_admin_perm = ctx.author.guild_permissions.administrator
        has_incense_admin_role = discord.utils.get(ctx.author.roles, name="Incense Admin") is not None

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot buy a incense while in trade.")
            return

        if not has_admin_perm and not has_incense_admin_role:
            await ctx.send(
                "You need to have Administrator permissions or the 'Incense Admin' role to use this command.")
            return

        # Check both bot cache and DB to see if incense is already running
        if (str(ctx.channel.id) in self.bot.channel_spawns and self.bot.channel_spawns[str(ctx.channel.id)].get(
                "from_incense", False)) or \
                await self.incense_exists_in_db(ctx.channel.id):
            await ctx.send("This channel already has a running incense.")
            return

        incense_costs = {
            ("1h", "10s"): 100,
            ("1h", "20s"): 50,
            ("1h", "30s"): 30,
            ("3h", "10s"): 300,
            ("3h", "20s"): 150,
            ("3h", "30s"): 90
        }
        spawn_times = {
            ("1h", "10s"): 360,
            ("1h", "20s"): 180,
            ("1h", "30s"): 90,
            ("3h", "10s"): 1080,
            ("3h", "20s"): 540,
            ("3h", "30s"): 270
        }

        if action != "buy":
            await ctx.send("Invalid action. Use `buy` to purchase incense.")
            return

        if (duration, interval) not in incense_costs:
            await ctx.send("Invalid duration or interval. Please choose valid options.")
            return

        cost = incense_costs[(duration, interval)]
        total_spawns = spawn_times[(duration, interval)]

        user_shards = await self.get_user_shards(ctx.author.id)
        if user_shards < cost:
            await ctx.send(f"You do not have enough shards. You need {cost} shards to buy incense.")
            return

        await ctx.send(f"Confirm purchase: {duration} incense with {interval} interval for {cost} shards. (y/n)")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in ['y', 'n']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() == 'n':
                await ctx.send("Purchase cancelled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("No response, purchase cancelled.")
            return

        await self.deduct_user_shards(ctx.author.id, cost)
        await self.add_incense_to_db(ctx.guild.id, ctx.channel.id, total_spawns, total_spawns, interval)

        await ctx.send(
            f"Purchase successful! {total_spawns} Pokémon will spawn at {interval} intervals for {duration}.")

        await self.spawn_pokemon(ctx, duration, interval, total_spawns, from_incense=True)

    @commands.command()
    @is_not_suspended()
    async def start_infinite(self, ctx):
        allowed_users = [688983124868202496, 760720549092917248]
        if ctx.author.id not in allowed_users:
            await ctx.send("You don't have permission to use this command.")
            return

        started_channels = []
        for channel_id in INFINITE_CHANNELS:
            if channel_id in self.bot.infinite_incense_channels:
                continue

            self.bot.infinite_incense_channels.add(channel_id)
            self.bot.channel_spawns[str(channel_id)] = {"infinite": True}
            started_channels.append(channel_id)
            asyncio.create_task(self.spawn_infinite(channel_id))

        if started_channels:
            await ctx.send("Infinite incense has started in all designated channels!")
        else:
            await ctx.send("Infinite incense is already running in all designated channels.")

    async def monitor_incense(self):
        await self.bot.wait_until_ready()
        self.bot.active_incense_tasks = {}  # Store active incense tasks

        while not self.bot.is_closed():
            async with self.bot.db.pool.acquire() as conn:
                active_incenses = await conn.fetch(
                    "SELECT channel_id, spawn_remaining, interval, paused FROM incense WHERE spawn_remaining > 0"
                )

            for record in active_incenses:
                channel_id = record["channel_id"]
                channel = self.bot.get_channel(channel_id)

                if channel and not record["paused"]:
                    if channel_id not in self.bot.active_incense_tasks:  # Prevent duplicate tasks
                        self.bot.active_incense_tasks[channel_id] = self.bot.loop.create_task(
                            self.spawn_pokemon(channel, "incense", record["interval"], record["spawn_remaining"], True)
                        )

            await asyncio.sleep(10)

    async def spawn_pokemon(self, channel, duration, interval, total_spawns, from_incense=False):
        channel_id = channel.id

        async with self.bot.db.pool.acquire() as conn:
            incense_data = await conn.fetchrow(
                "SELECT spawn_remaining, paused FROM incense WHERE channel_id = $1",
                channel_id
            )

        if not incense_data:
            return

        spawn_remaining = incense_data["spawn_remaining"]

        while spawn_remaining > 0:
            async with self.bot.db.pool.acquire() as conn:
                incense_data = await conn.fetchrow(
                    "SELECT paused FROM incense WHERE channel_id = $1",
                    channel_id
                )
                if incense_data and incense_data["paused"]:
                    await asyncio.sleep(5)
                    continue

            pokemon_name = fetch_pokemon_name()
            if not pokemon_name:
                await channel.send("Error: Could not select a Pokémon.")
                return

            base_stats = get_base_stats(pokemon_name)
            if not base_stats:
                await channel.send(f"Error: Could not fetch stats for {pokemon_name}.")
                return

            image_path = await self.download_random_image(pokemon_name)
            if not image_path:
                await channel.send(f"Image missing for {pokemon_name}.")
                return

            self.bot.channel_spawns[str(channel_id)] = {
                "name": pokemon_name,
                "base_stats": base_stats,
                "infinite": True
            }

            file = discord.File(image_path, filename="pokemon.png")

            embed = discord.Embed(
                title="A wild Pokémon has appeared!",
                description="Guess the Pokémon using `Pokédia#2537 catch <name>`",
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Spawns remaining: {spawn_remaining} | Interval: {interval}")
            embed.set_image(url="attachment://pokemon.png")

            await channel.send(embed=embed, file=file)

            os.unlink(image_path)

            async with self.bot.db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE incense SET spawn_remaining = spawn_remaining - 1 WHERE channel_id = $1",
                    channel_id
                )
                spawn_remaining = await conn.fetchval(
                    "SELECT spawn_remaining FROM incense WHERE channel_id = $1",
                    channel_id
                )

            if not spawn_remaining or spawn_remaining <= 0:
                async with self.bot.db.pool.acquire() as conn:
                    await conn.execute("DELETE FROM incense WHERE channel_id = $1", channel_id)
                return

            await asyncio.sleep(int(interval))

    async def spawn_infinite(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            print(f"[Spawn] Channel {channel_id} not found.")
            return

        print(f"[Spawn] Starting infinite spawns in channel {channel_id}.")

        while True:
            try:
                pokemon_name = fetch_pokemon_name()
                if not pokemon_name:
                    await channel.send("Error: Could not select a Pokémon.")
                    await asyncio.sleep(5)
                    continue

                base_stats = get_base_stats(pokemon_name)
                if not base_stats:
                    await channel.send(f"Error: Could not fetch stats for {pokemon_name}.")
                    await asyncio.sleep(5)
                    continue

                image_path = await self.download_random_image(pokemon_name)
                if not image_path:
                    await channel.send(f"Image missing for {pokemon_name}.")
                    await asyncio.sleep(5)
                    continue

                file = discord.File(image_path, filename="pokemon.png")

                embed = discord.Embed(
                    title="A wild Pokémon has appeared!",
                    description="Guess the Pokémon using `Pokédia#2537 catch <name>`",
                    color=discord.Color.green(),
                )
                embed.set_footer(text="Spawns: infinite | Interval: 20s")
                embed.set_image(url="attachment://pokemon.png")

                await channel.send(embed=embed, file=file)

                os.unlink(image_path)

                self.bot.channel_spawns[str(channel_id)] = {
                    "name": pokemon_name,
                    "base_stats": base_stats
                }

                await asyncio.sleep(20)

            except Exception as e:
                print(f"[Spawn ERROR] Exception in channel {channel_id}: {e}")
                await asyncio.sleep(10)


async def setup(bot):
    await bot.add_cog(IncenseCommand(bot))
