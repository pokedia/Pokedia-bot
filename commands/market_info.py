import discord
from discord.ext import commands
import os
from utils.susp_check import is_not_suspended

class MarketInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='market_info', aliases=["mi"])
    @is_not_suspended()
    async def market_info(self, ctx, market_id: int):
        """Fetch Pokémon data from the PostgreSQL market table and display details."""

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot info a Pokémon from the market while in an active trade.")
            return

        # Ensure the database connection exists
        if not hasattr(self.bot, "db") or self.bot.db is None:
            print("MarketInfo: Database connection is not available!")
            await ctx.send("❌ Error: Database connection is not available!")
            return

        query = """
        SELECT marketid, ownerid, price, pokemon_name, level, xp, max_xp, total_iv_percent, 
               hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
               hp, attack, defense, spatk, spdef, speed,
               shiny, fusionable
        FROM market WHERE marketid = $1;
        """

        try:
            async with self.bot.db.pool.acquire() as conn:
                row = await conn.fetchrow(query, market_id)

            if not row:
                await ctx.send(f"❌ No Pokémon found with Market ID `{market_id}`.")
                return

            # Extract Pokémon data
            name = row['pokemon_name']
            level = row['level']
            xp = row['xp']
            max_xp = row['max_xp']
            total_iv_percent = row['total_iv_percent']
            is_shiny = row['shiny']
            is_fusionable = row['fusionable']
            price = row['price']

            # Construct stats string
            stats_str = (
                f"**HP**: {row['hp']} - IV {row['hp_iv']}/31\n"
                f"**Attack**: {row['attack']} - IV {row['attack_iv']}/31\n"
                f"**Defense**: {row['defense']} - IV {row['defense_iv']}/31\n"
                f"**Sp. Atk**: {row['spatk']} - IV {row['spatk_iv']}/31\n"
                f"**Sp. Def**: {row['spdef']} - IV {row['spdef_iv']}/31\n"
                f"**Speed**: {row['speed']} - IV {row['speed_iv']}/31\n"
                f"**Total IV**: {total_iv_percent}%"
            )

            # Add emojis based on conditions
            emoji_prefix = "✨" if is_shiny else ""
            emoji_prefix += "🧬" if is_fusionable else ""

            # Determine the image URL
            image_name = name.lower().replace(" ", "-")
            file = None  # Default to no local file

            if is_shiny:
                image_path = f"shiny/{image_name}/shiny_{image_name}.png"
                if os.path.exists(image_path):
                    file = discord.File(image_path, filename="pokemon.png")
                    image_url = "attachment://pokemon.png"
                else:
                    image_url = f"https://github.com/pokedia/images/blob/main/pokemon_shiny/{image_name}.png?raw=true&v=4"
            else:
                image_url = f"https://github.com/pokedia/images/blob/main/pokemon_images/{image_name}.png?raw=true&v=5"

            # Create an embed message
            embed = discord.Embed(
                title=f"Level {level} {emoji_prefix} {name}",
                description=f"**XP**: {xp}/{max_xp}",
                color=discord.Color.blue()
            )
            embed.add_field(name="**Stats**", value=stats_str, inline=False)
            embed.add_field(name="**Price**", value=f"{price} Pokécash", inline=True)
            embed.add_field(name="**Market ID**", value=f"{market_id}", inline=True)
            embed.set_image(url=image_url)

            # Send the embed message with or without an attachment
            if file:
                await ctx.send(file=file, embed=embed)
            else:
                await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
            print(f"Database error: {e}")

# Add the cog to the bot
async def setup(bot):
    print(f"✅ MarketInfo Cog Loaded - bot.db: {bot.db}")
    await bot.add_cog(MarketInfo(bot))
