import discord
from discord.ext import commands
from utils.susp_check import is_not_suspended

class UnfavoriteCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["unfav"])
    @is_not_suspended()
    async def unfavorite(self, ctx, pokemon_id: int):
        user_id = ctx.author.id

        async with self.bot.db.pool.acquire() as conn:
            # Check if the Pokémon exists and is favorited
            result = await conn.fetchrow(
                "SELECT favorite FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2", user_id, pokemon_id
            )

            if not result:
                return await ctx.send(f"❌ You don't own a Pokémon with ID `{pokemon_id}`.")

            if not result["favorite"]:
                return await ctx.send(f"⚠️ Pokémon `{pokemon_id}` is not favorited.")

            # Update the favorite status
            await conn.execute(
                "UPDATE users_pokemon SET favorite = false WHERE userid = $1 AND pokemon_id = $2", user_id, pokemon_id
            )

        await ctx.send(f"✅ Pokémon `{pokemon_id}` has been unfavorited.")

# Add the command to the bot
async def setup(bot):
    await bot.add_cog(UnfavoriteCommand(bot))
