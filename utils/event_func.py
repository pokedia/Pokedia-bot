# store active game per user
spot_answer = {}
dodge = {}
find_star = {}

import discord
import asyncio
import random


EVENT_REWARDS = {
    1: {"santa_box": 1, "pokecash": 500},
    2: {"santa_box": 1, "pokecash": 500},
    3: {"santa_box": 3, "pokecash": 1000},
    4: {"santa_box": 5, "pokecash": 2000},
    5: {"santa_box": 5, "pokecash": 2000},
    6: {"santa_box": 0, "pokecash": 500},
    7: {"santa_box": 2, "pokecash": 1000}
}

# GitHub base URL
GITHUB_BASE = "https://raw.githubusercontent.com/pokedia/images/main/spot_santa"
DEFAULT_URL = f"{GITHUB_BASE}/default.png"

async def spot_the_santa(ctx, spot_answer):
    user_id = ctx.author.id

    if user_id in find_star:
        await ctx.send("⏳ Finish your current event game first!")
        return

    if user_id in dodge:
        await ctx.send(
            embed=discord.Embed(
                title="⏳ Game Already Running",
                description="Finish your current **Dodge the Snowball** game first!",
                color=discord.Color.orange()
            )
        )
        return

    if user_id in spot_answer:
        await ctx.send(
            embed=discord.Embed(
                title="⏳ Game Already Running",
                description="Finish your current **Spot The Santa** game first!",
                color=discord.Color.orange()
            )
        )
        return

    # Acquire a connection from the bot's pool
    async with ctx.bot.db.pool.acquire() as conn:
        # 1️⃣ Check Snow Coin
        row = await conn.fetchrow(
            "SELECT value FROM inventory WHERE userid = $1 AND item_name = $2",
            user_id, "Snow Coin"
        )
        if not row or row["value"] < 1:
            await ctx.send(
                embed=discord.Embed(
                    title="❄️ Insufficient Snow Coins",
                    description="You need **1 Snow Coin** to play Spot The Santa.",
                    color=discord.Color.red()
                )
            )
            return

        # 2️⃣ Deduct 1 Snow Coin
        await conn.execute(
            "UPDATE inventory SET value = value - 1 WHERE userid = $1 AND item_name = $2",
            user_id, "Snow Coin"
        )

    # 3️⃣ Pick random grid number (1–10)
    chosen_number = random.randint(1, 10)
    image_name = f"grid{chosen_number}.png"
    spot_answer[user_id] = image_name

    grid_url = f"https://raw.githubusercontent.com/pokedia/images/main/spot_santa/{image_name}"
    default_url = "https://raw.githubusercontent.com/pokedia/images/main/spot_santa/default.png"

    # Send grid embed
    embed = discord.Embed(
        title="🎅 Spot The Santa (Memory Game)",
        description="Memorize the positions!\nYou have **3 seconds** 👀",
        color=discord.Color.blue()
    )
    embed.set_image(url=grid_url)
    msg = await ctx.send(embed=embed)

    # Wait 3 seconds
    await asyncio.sleep(5)

    # Show default image
    new_embed = discord.Embed(
        title="🎅 Spot The Santa (Memory Game)",
        description="Where were the Santas?\nReply with positions like `B2 C3`",
        color=discord.Color.blurple()
    )
    new_embed.set_image(url=default_url)
    await msg.edit(embed=new_embed)


async def event_reward(ctx, user_id: int, reward_number: int):
    if reward_number not in EVENT_REWARDS:
        return False  # invalid reward

    reward = EVENT_REWARDS[reward_number]
    santa_boxes = reward["santa_box"]
    pokecash = reward["pokecash"]

    async with ctx.bot.db.pool.acquire() as conn:
        async with conn.transaction():
            # 🎁 Add / Update Santa Box in inventory
            await conn.execute(
                """
                INSERT INTO inventory (userid, item_name, value)
                VALUES ($1, 'Santa Box', $2)
                ON CONFLICT (userid, item_name)
                DO UPDATE SET value = inventory.value + EXCLUDED.value
                """,
                user_id, santa_boxes
            )

            # 💰 Add Pokecash to users table
            await conn.execute(
                """
                UPDATE users
                SET pokecash = pokecash + $1
                WHERE userid = $2
                """,
                pokecash, user_id
            )

    return True

async def dodge_the_snowball(ctx, dodge):
    user_id = ctx.author.id

    # ⛔ Prevent multiple games
    if user_id in find_star:
        await ctx.send("⏳ Finish your current event game first!")
        return

    if user_id in dodge:
        await ctx.send(
            embed=discord.Embed(
                title="⏳ Game Already Running",
                description="Finish your current **Dodge the Snowball** game first!",
                color=discord.Color.orange()
            )
        )
        return

    if user_id in spot_answer:
        await ctx.send(
            embed=discord.Embed(
                title="⏳ Game Already Running",
                description="Finish your current **Spot The Santa** game first!",
                color=discord.Color.orange()
            )
        )
        return

    # Acquire a connection from the bot's pool
    async with ctx.bot.db.pool.acquire() as conn:
        # 1️⃣ Check Snow Coin
        row = await conn.fetchrow(
            "SELECT value FROM inventory WHERE userid = $1 AND item_name = $2",
            user_id, "Snow Coin"
        )

        if not row or row["value"] < 1:
            await ctx.send(
                embed=discord.Embed(
                    title="❄️ Insufficient Snow Coins",
                    description="You need **1 Snow Coin** to play **Dodge the Snowball**.",
                    color=discord.Color.red()
                )
            )
            return

        # 2️⃣ Deduct 1 Snow Coin
        await conn.execute(
            "UPDATE inventory SET value = value - 1 WHERE userid = $1 AND item_name = $2",
            user_id, "Snow Coin"
        )

    # 3️⃣ Pick random dangerous tile (1–3)
    danger_tile = random.randint(1, 3)
    dodge[user_id] = danger_tile

    image_url = "https://raw.githubusercontent.com/pokedia/images/main/spot_santa/dodge.png"

    # 4️⃣ Send game embed
    embed = discord.Embed(
        title="❄️ Dodge the Snowball!",
        description=(
            "A snowball is about to be thrown! ☃️💥\n\n"
            "Choose **one tile** to dodge the attack:\n\n"
            "🔹 **Top Tile** → `1`\n"
            "🔹 **Middle Tile** → `2`\n"
            "🔹 **Bottom Tile** → `3`\n\n"
            "Respond using:\n"
            "`@Pokédia#2537 dodge <number>`"
        ),
        color=discord.Color.blue()
    )
    embed.set_image(url=image_url)

    await ctx.send(embed=embed)

async def find_the_star(ctx, find_star, number=None):
    user_id = ctx.author.id

    # ⭐ REWARD HANDLER (when called with number = 1)
    if number == 1:
        async with ctx.bot.db.pool.acquire() as conn:
            # Add 3 Santa Box
            await conn.execute(
                """
                INSERT INTO inventory (userid, item_name, value)
                VALUES ($1, 'Santa Box', 3)
                ON CONFLICT (userid, item_name)
                DO UPDATE SET value = inventory.value + 3
                """,
                user_id
            )

            # Add 1500 Pokecash
            await conn.execute(
                "UPDATE users SET pokecash = pokecash + 1500 WHERE userid = $1",
                user_id
            )

        # Remove from active game
        find_star.pop(user_id, None)

        # Send reward message
        await ctx.send(
            "🌟 **WOW! You Found the Golden Star!** 🌟\n\n"
            "Santa seems very happy 🎅✨\n\n"
            "**He gave you:**\n"
            "• 🎁 **3x Santa Box**\n"
            "• 💰 **1500 Pokecash**"
        )
        return

    # ⛔ Prevent multiple games
    if user_id in find_star:
        await ctx.send("⏳ Finish your current event game first!")
        return

    if user_id in dodge:
        await ctx.send(
            embed=discord.Embed(
                title="⏳ Game Already Running",
                description="Finish your current **Dodge the Snowball** game first!",
                color=discord.Color.orange()
            )
        )
        return

    if user_id in spot_answer:
        await ctx.send(
            embed=discord.Embed(
                title="⏳ Game Already Running",
                description="Finish your current **Spot The Santa** game first!",
                color=discord.Color.orange()
            )
        )
        return

    # Acquire a connection from the bot's pool
    async with ctx.bot.db.pool.acquire() as conn:
        # 1️⃣ Check Snow Coin
        row = await conn.fetchrow(
            "SELECT value FROM inventory WHERE userid = $1 AND item_name = $2",
            user_id, "Snow Coin"
        )

        if not row or row["value"] < 1:
            await ctx.send(
                "❄️ **Insufficient Snow Coins**\n"
                "You need **1 Snow Coin** to play **Find The Star**."
            )
            return

        # 2️⃣ Deduct 1 Snow Coin
        await conn.execute(
            "UPDATE inventory SET value = value - 1 WHERE userid = $1 AND item_name = $2",
            user_id, "Snow Coin"
        )

        # 3️⃣ Mark star as active
        await conn.execute(
            "UPDATE users SET star = true WHERE userid = $1",
            user_id
        )

    # 4️⃣ Mark game active
    find_star[user_id] = True

    # 5️⃣ Send normal message
    await ctx.send(
        "**🎄 Santa's Looking for his Golden Star** ⭐\n"
        "Can you find it?!\n\n"
        "Catch in the Wild to get the 📦 **Decor Box**, "
        "There is a chance you might find one inside it."
    )



