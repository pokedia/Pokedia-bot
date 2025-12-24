import discord
from discord.ext import commands
import asyncpg
from utils.susp_check import is_not_suspended

BOT_USER_ID = 1339891854279184404
SQL_CHANNEL_ID = 1370357756246364271

class SQLExecutor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore DMs, non-target channel, and non-bot messages
        if message.guild is None or message.channel.id != SQL_CHANNEL_ID:
            return
        if message.author.id != BOT_USER_ID:
            return

        # Look for code blocks containing SQL
        if message.content.startswith("```sql") and message.content.endswith("```"):
            raw_sql = message.content.strip("` ")
            sql_code = raw_sql[3:].strip()  # Remove the 'sql' language specifier

            try:
                await self.bot.db.execute(sql_code)
                await message.channel.send("✅ SQL executed successfully.")
            except Exception as e:
                await message.channel.send(f"❌ SQL execution error: {e}")


async def setup(bot):
    await bot.add_cog(SQLExecutor(bot))
