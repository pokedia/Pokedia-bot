import random
import discord
from discord.ext import commands
from utils.event_func import find_the_star, find_star

class DecorEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 📦 DECOR BOX OPEN COMMAND
    @commands.command(name="decoropen", aliases=["do"])
    async def decoropen(self, ctx):
        user_id = ctx.author.id

        async with ctx.bot.db.pool.acquire() as conn:
            # 1️⃣ Check Decor Box
            row = await conn.fetchrow(
                "SELECT value FROM inventory WHERE userid = $1 AND item_name = $2",
                user_id, "Decor Box"
            )

            if not row or row["value"] < 1:
                await ctx.send(
                    embed=discord.Embed(
                        title="📦 No Decor Box Found",
                        description="You don't have any **Decor Boxes** to open!",
                        color=discord.Color.red()
                    )
                )
                return

            # 2️⃣ Deduct Decor Box
            await conn.execute(
                "UPDATE inventory SET value = value - 1 WHERE userid = $1 AND item_name = $2",
                user_id, "Decor Box"
            )

            # 3️⃣ Roll reward
            roll = random.random() * 100

            # 🎄 Decorations — 90%
            if roll <= 60:
                reward_name = "Decorations"
                await conn.execute(
                    """
                    INSERT INTO inventory (userid, item_name, value)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (userid, item_name)
                    DO UPDATE SET value = inventory.value + 1
                    """,
                    user_id, reward_name
                )

            # ⭐ Golden Star — 9%
            elif roll <= 99:
                reward_name = "Golden Star"

                # Trigger star hunt
                await find_the_star(ctx, find_star, 1)

                # Star found → set false
                await conn.execute(
                    "UPDATE users SET star = false WHERE userid = $1",
                    user_id
                )

            # 🍬 Candy Cane — 1%
            else:
                reward_name = "Candy Cane"
                await conn.execute(
                    """
                    INSERT INTO inventory (userid, item_name, value)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (userid, item_name)
                    DO UPDATE SET value = inventory.value + 1
                    """,
                    user_id, reward_name
                )

        # 4️⃣ Result embed
        embed = discord.Embed(
            title="🎁 You Opened a 📦 Decor Box!",
            description=f"• **{reward_name}**",
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DecorEvent(bot))
