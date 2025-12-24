import discord
from discord.ext import commands

class EventReward(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.command(name="event", aliases=["ev"])
    async def event_reward(self, ctx):
        user_id = int(ctx.author.id)
        amount = 1  # Give 1 Event Box

        # Check if user is eligible (points >= 100)
        points = await self.db.fetchval(
            "SELECT points FROM event WHERE owner_id = $1",
            user_id
        )

        if points is None or points < 100:
            return await ctx.send("❌ You need at least **100 points** in the event to claim this reward.")

        # Check if any Event Box row exists for user, regardless of value
        existing = await self.db.fetchval(
            "SELECT 1 FROM inventory WHERE userid = $1 AND item_name = 'Event Box' LIMIT 1",
            user_id
        )

        if existing is not None:
            return await ctx.send("🎁 You have already claimed your **Event Box**.")

        # Insert new Event Box
        await self.db.execute(
            "INSERT INTO inventory (userid, item_name, value) VALUES ($1, 'Event Box', $2)",
            user_id, amount
        )

        embed = discord.Embed(
            title="🎉 Event Reward",
            description="You received **1 Event Box**!",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EventReward(bot, bot.db))

