import json
import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class ShinyHunt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alias_file = "functions/alias.json"
        self.rarity_file = "spawn_rarity.json"

    def load_aliases(self):
        """Load aliases from alias.json"""
        try:
            with open(self.alias_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_spawn_rarity(self):
        """Load spawn rarity from spawn_rarity.json"""
        try:
            with open(self.rarity_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def find_main_pokemon(self, search_name):
        """Finds the correct Pokémon name from aliases"""
        aliases = self.load_aliases()
        search_name = search_name.lower().replace(" ", "-")

        for main_name, alias_list in aliases.items():
            if search_name in [name.lower() for name in alias_list] or search_name == main_name.lower():
                return main_name.replace("-", " ")
        return None

    def is_valid_pokemon(self, pokemon_name):
        """Check if the Pokémon is valid based on spawn rarity"""
        spawn_rarity_data = self.load_spawn_rarity()
        pokemon_name = pokemon_name.lower().replace(" ", "-")

        for entry in spawn_rarity_data:
            if entry["pokemon"].lower().replace(" ", "-") == pokemon_name:
                return True
        return False

    @commands.command(name="shinyhunt", aliases=["sh"])
    @is_not_suspended()
    async def shiny_hunt(self, ctx, *, pokemon_name: str = None):
        user_id = ctx.author.id

        # If no Pokémon name is given, show current shiny hunt
        if not pokemon_name:
            query = "SELECT shiny_hunt, streak FROM users WHERE userid = $1"
            result = await self.bot.db.fetchrow(query, user_id)

            if result and result["shiny_hunt"]:
                embed = discord.Embed(
                    title=f"You are currently hunting {result['shiny_hunt']}",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Shiny Hunt", value=result["shiny_hunt"], inline=True)
                embed.add_field(name="Streak", value=result["streak"], inline=True)

                await ctx.send(embed=embed)
            else:
                await ctx.send("You are not currently shiny hunting any Pokémon.")
            return

        # Validate Pokémon name using alias.json
        main_pokemon = self.find_main_pokemon(pokemon_name)
        if not main_pokemon:
            await ctx.send("You can't shiny hunt an incorrect Pokémon!")
            return

        # Validate Pokémon name using spawn_rarity.json
        if not self.is_valid_pokemon(main_pokemon):
            await ctx.send("You cannot shiny hunt a Non-Catchable Pokemon.")
            return

        # Check current shiny hunt in the database
        query = "SELECT shiny_hunt FROM users WHERE userid = $1"
        current_hunt = await self.bot.db.fetchval(query, user_id)

        # If user is already hunting a different Pokémon, confirm reset
        if current_hunt and current_hunt.lower() != main_pokemon.lower():
            await ctx.send("Are you sure you want to switch your shiny hunt? It will reset your streak! Confirm by typing **y** or **n**.")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["y", "n"]

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
                if msg.content.lower() == "y":
                    await self.bot.db.execute(
                        "UPDATE users SET shiny_hunt = $1, streak = 0 WHERE userid = $2",
                        main_pokemon, user_id
                    )
                    await ctx.send(f"Your shiny hunt has been switched to **{main_pokemon}**! Streak has been reset.")
                else:
                    await ctx.send("Shiny hunt change cancelled.")
            except TimeoutError:
                await ctx.send("Confirmation timed out. Your shiny hunt remains unchanged.")
            return

        # Start new shiny hunt if no hunt is active
        await self.bot.db.execute(
            "UPDATE users SET shiny_hunt = $1, streak = 0 WHERE userid = $2",
            main_pokemon, user_id
        )

        await ctx.send(f"You are now shiny hunting **{main_pokemon}**!")

async def setup(bot):
    await bot.add_cog(ShinyHunt(bot))
