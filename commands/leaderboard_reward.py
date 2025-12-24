import discord
from discord.ext import commands

class LeaderboardReward(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.command(name="lb", aliases=["leaderboard"])
    async def lb_reward(self, ctx, action: str = None):
        if action != "reward":
            return

        user_id = int(ctx.author.id)
        allowed_users = {780861103566880778, 688448419400122439, 1300082905292472430}  # Replace with actual user IDs

        if user_id not in allowed_users:
            return await ctx.send("❌ You are not eligible to claim this reward at the moment.")

        # Check if any row exists with 'Suprise Box' for the user, regardless of value
        existing = await self.db.fetchval(
            "SELECT 1 FROM inventory WHERE userid = $1 AND item_name = 'Suprise Box' LIMIT 1",
            user_id
        )

        if existing is not None:
            return await ctx.send("🎁 You have already claimed your **Suprise Boxes**.")

        # Insert new record with 3 Suprise Boxes
        amount = 3
        await self.db.execute(
            "INSERT INTO inventory (userid, item_name, value) VALUES ($1, 'Suprise Box', $2)",
            user_id, amount
        )

        embed = discord.Embed(
            title="🎁 Leaderboard Reward",
            description="You received **3 Suprise Boxes**!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardReward(bot, bot.db))

