import discord
from discord.ext import commands
import re
from utils.susp_check import is_not_suspended

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Use the bot's database connection

    @commands.command(name="nick")
    @is_not_suspended()
    async def nick_command(self, ctx, action: str, pokemon_id: str, *, nickname: str = None):
        """Sets or resets a nickname for a Pokémon based on its ID in the database."""

        user_id = ctx.author.id  # User's Discord ID (bigint in DB)

        # Attempt to convert pokemon_id to int
        try:
            pokemon_id = int(pokemon_id)
        except ValueError:
            await ctx.send("Please provide a valid Pokémon ID as a number.")
            return

        # Debugging: Print user_id and pokemon_id
        print(f"User ID: {user_id}, Pokémon ID: {pokemon_id}")

        # Check if the Pokémon exists for this user
        pokemon = await self.db.fetchrow(
            "SELECT pokemon_name FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
            user_id, pokemon_id
        )

        # Debugging: Print the fetched Pokémon
        print(f"Fetched Pokémon: {pokemon}")

        if not pokemon:
            await ctx.send("No Pokémon found with this ID under your ownership.")
            return

        if action.lower() == "reset":
            # Reset nickname to NULL
            await self.db.execute(
                "UPDATE users_pokemon SET nickname = NULL WHERE userid = $1 AND pokemon_id = $2",
                user_id, pokemon_id
            )
            embed = discord.Embed(
                description=f"`{pokemon['pokemon_name']}`'s nickname has been reset.",
                color=discord.Color.dark_theme()
            )
            await ctx.send(embed=embed)
            return

        if action.lower() != "set":
            await ctx.send("Invalid action. Use `set` to set a nickname or `reset` to remove it.")
            return

        if not nickname:
            await ctx.send("You must provide a nickname or use `reset` to remove it.")
            return

        # Validate nickname (No URLs, GIFs, or images)
        if re.search(r'https?://|\.gif|\.png|\.jpg|\.jpeg', nickname, re.IGNORECASE):
            await ctx.send("Nicknames cannot contain URLs or image links.")
            return

        # Update nickname in the database
        await self.db.execute(
            "UPDATE users_pokemon SET nickname = $1 WHERE userid = $2 AND pokemon_id = $3",
            nickname, user_id, pokemon_id
        )

        embed = discord.Embed(
            description=f"`{pokemon['pokemon_name']}`'s nickname has been set to **`{nickname}`**",
            color=discord.Color.dark_theme()
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Nickname(bot))
