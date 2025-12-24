import discord
import json
from discord.ext import commands
from utils.embed_utils import create_starters_embed
from utils.susp_check import is_not_suspended

class StartCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database_path = "database.json"  # Path to the database file

    def has_started(self, user_id):
        """Check if the user has already started their journey."""
        try:
            with open(self.database_path, "r") as f:
                database = json.load(f)
            user_data = database.get(str(user_id), {})
            return "pokemon" in user_data and len(user_data["pokemon"]) > 0
        except (FileNotFoundError, json.JSONDecodeError):
            return False  # Assume the user hasn't started if the file is missing or corrupted

    @commands.command(name="start")
    @is_not_suspended()
    async def start_command(self, ctx):
        """Displays an embed with Gen 1 to Gen 9 Pokémon starters."""
        user_id = ctx.author.id

        if self.has_started(user_id):
            await ctx.send("You have already started your journey.")
        else:
            embed = await create_starters_embed(self.bot)  # Pass bot instance to fetch emojis
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StartCommand(bot))


