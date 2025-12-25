import discord
from discord.ext import commands
import os
from database import Database
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get token from environment
DISCORD_TOKEN = os.getenv("DISCORD_BOT")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_BOT token not found in .env file")

# Create bot instance
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("p!"),
    intents=intents,
    help_command=None
)

# Initialize PostgreSQL Database
bot.db = Database(
    dsn="postgresql://postgres:Pokedia_1166@database-1.cv44m6k2o5b9.ap-southeast-2.rds.amazonaws.com:5432/postgres"
)

# Function to load extensions
async def load_extensions():
    try:
        await bot.load_extension("commands.trading")
        print("Loaded trading.py")
    except Exception as e:
        print(f"Failed to load trading.py: {e}")

    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "trading.py":
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                print(f"Loaded {filename}")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

# Event for when bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

# Main function
async def main():
    async with bot:
        await bot.db.connect()
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot is shutting down gracefully.")
