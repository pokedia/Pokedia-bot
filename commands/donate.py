import discord
from discord.ext import commands

# Emoji ID map
INGREDIENT_EMOJIS = {
    "rice": ("rice", 1365954853834199132),
    "vegetables": ("vegetables", 1365955281560928326),
    "fruits": ("fruits", 1365954809869373491),
    "soyasauce": ("soyasauce", 1365954843717668874),
    "cookingoil": ("cookingoil", 1365956057846906901),
    "syrupsauce": ("syrupsauce", 1365954832925724712),
    "sugar": ("sugar", 1365954858695262249),
    "salt": ("salt", 1365954850508243045),
    "butter": ("butter", 1365954822947475476),
    "egg": ("egg", 1365954820199944202),
    "flour": ("flour", 1365954837686128710),
    "milk": ("milk", 1365954846485909585),
    "cheese": ("cheese", 1365954828118790217),
    "colddrink": ("colddrink", 1365954804098142309)
}

def get_emoji(ingredient):
    data = INGREDIENT_EMOJIS.get(ingredient)
    if data:
        name, emoji_id = data
        return f"<:{name}:{emoji_id}>"
    return ""

class Donate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='donate')
    async def donate(self, ctx, from_ingredient: str, to_ingredient: str, amount: int):
        if amount <= 0:
            return await ctx.send("Amount must be greater than 0.")

        from_ingredient = from_ingredient.lower().replace(" ", "")
        to_ingredient = to_ingredient.lower().replace(" ", "")
        user_id = ctx.author.id
        required_amount = amount * 4

        async with self.bot.db.pool.acquire() as conn:
            # Check if both columns exist
            valid_columns = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'event'
                    AND column_name = $1
                ) AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'event'
                    AND column_name = $2
                )
            """, from_ingredient, to_ingredient)

            if not valid_columns:
                return await ctx.send("One or both of the ingredient names are invalid.")

            # Get user's amount of from_ingredient
            row = await conn.fetchrow(
                f"SELECT {from_ingredient} FROM event WHERE owner_id = $1", user_id
            )

            if not row:
                return await ctx.send("You have no ingredients recorded.")

            current_amount = row[from_ingredient]
            if current_amount is None or current_amount < required_amount:
                return await ctx.send(f"You need at least {required_amount} {from_ingredient} to donate.")

            # Perform the donation conversion
            await conn.execute(
                f"""
                UPDATE event
                SET {from_ingredient} = {from_ingredient} - $1,
                    {to_ingredient} = COALESCE({to_ingredient}, 0) + $2
                WHERE owner_id = $3
                """,
                required_amount, amount, user_id
            )

        embed = discord.Embed(
            title="Donation Successful!",
            description=(
                f"You donated **x{required_amount}** {get_emoji(from_ingredient)} `{from_ingredient.title()}` and received:\n\n"
                f"• {get_emoji(to_ingredient)} **x{amount}** `{to_ingredient.title()}`"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Donate(bot))


