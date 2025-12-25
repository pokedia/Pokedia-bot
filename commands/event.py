import discord
from discord.ext import commands
from utils.event_func import spot_the_santa, spot_answer, event_reward, dodge_the_snowball, dodge, find_the_star, find_star
from spot_santa_answers import spot_santa_answers

TILE_EMOJIS = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
}

EVENT_REWARDS = {
    1: {"santa_box": 1, "pokecash": 500},
    2: {"santa_box": 1, "pokecash": 500},
    3: {"santa_box": 3, "pokecash": 1000},
    4: {"santa_box": 5, "pokecash": 2000},
    5: {"santa_box": 5, "pokecash": 2000},
}

# 🔗 GitHub RAW base (YOUR repo)
GITHUB_BASE = "https://raw.githubusercontent.com/pokedia/images/main/spot_santa"

COVER_URL = f"{GITHUB_BASE}/cover.png"
DEFAULT_URL = f"{GITHUB_BASE}/default.png"
DODGE_URL = f"{GITHUB_BASE}/dodge.png"

class GamesDropdown(discord.ui.Select):
    def __init__(self, author_id: int):
        self.author_id = author_id
        options = [
            discord.SelectOption(label="Spot The Santa", description="Test your memory skills", emoji="🎅"),
            discord.SelectOption(label="Fill Up The Spaces", description="Coming Soon", emoji="⚫"),
            discord.SelectOption(label="Dodge the Snowball", description="Test your Luck", emoji="❄️"),
            discord.SelectOption(label="Find the Golden Star", description="Coming Soon", emoji="🌟"),
        ]

        super().__init__(
            placeholder="🎮 Games",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        # 🔒 Only command author can use this menu
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the user who ran this command can use this menu.",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        choice = self.values[0]

        if choice == "Spot The Santa":
            embed = discord.Embed(
                title="🎅 Spot The Santa",
                description=(
                    "**Spot The Santa** is a memory-based game.\n"
                    "You will be shown a grid with Santa hidden in 5 positions.\n"
                    "Memorize carefully — after **3 seconds**, the grid will be covered!\n\n"
                    "**Prize System:**\n"
                    "`4 or 5 Positions Right:` 5x Santa Box; 2000 Pokecash\n"
                    "`3 Positions Right:` 3x Santa Box; 1000 Pokecash\n"
                    "`1 or 2 Positions Right:` 1x Santa Box; 500 Pokecash\n\n"
                    "Use the command `@Pokédia#2537 event solve {your guess}` for eg: b2,a1,a3 etc."
                ),
                color=discord.Color.blue()
            )
            embed.set_image(url=DEFAULT_URL)

        elif choice == "Dodge the Snowball":
            embed = discord.Embed(
                title="❄️ Dodge The Snowball",
                description=(
                    "**Dodge The Snowball** is a Luck-based game.\n\n"
                    "You will be shown 3 Tiles, Out of which 1 Tile is **DANGER**.\n\n"
                    "Choose your Tile Carefully and **BE SAFE FROM THE SNOWBALL!**\n\n"
                    "**Prize System:**\n"
                    "`Safe`: 2x Santa Box; 1000 Pokecash\n"
                    "`Hit`: 0x Santa Box; 500 Pokecash\n\n"
                    "Use the command `@Pokédia#2537 event dodge {tile_number}`"
                ),
                color=discord.Color.blue()
            )
            embed.set_image(url=DODGE_URL)

        elif choice == "Find the Golden Star":
            embed = discord.Embed(
                title="🌟 Find the Golden Star",
                description=(
                    "**Help Santa find his `LOST STAR`**.\n\n"
                    "You will receive Decor Box while catching in the wild.\n\n"
                    "Open those boxes and have a chance to find the Golden Star!**\n\n"
                    "**Prize System:**\n"
                    "If you box a Golden Star, You wi automatically receive your **REWARD**\n"
                    "`3x Santa Box; 1500 Pokecash`\n\n"
                    "Use the command `@Pokédia#2537 decoropen/do` to open the Decor Box."
                ),
                color=discord.Color.blue()
            )

        else:
            embed = discord.Embed(
                title=choice,
                description="🚧 **Coming Soon!**\nSanta is still preparing this game 🎄",
                color=discord.Color.orange()
            )

        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self.view
        )


class GamesView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.add_item(GamesDropdown(author_id))


class ChristmasEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["ev"])
    async def event(self, ctx, subcommand=None, *, args=None):
        """Main event command with subcommands 'play' and 'solve'"""
        if subcommand is None:
            # Show the main games menu
            embed = discord.Embed(
                title="🎄 Pokedia Christmas Sports 🎄",
                description=(
                    "*Waiting for Santa’s gift? Well, Santa seems to be in the mood for some exercise — "
                    "**not alone, but with all of you!**"
                    "Participate in various **Christmas Sports** and earn different and better rewards "
                    "based on your performance*.\n\n\n"
                    ":video_game: **Christmas Sports you can play:**\n"
                    "**1.** *Spot the Santa* :santa:\n"
                    "**2.** *Fill Up The Spaces* :black_circle:\n"
                    "**3.** *Dodge the Snowball* :snowflake:\n"
                    "**4.** *Find the Golden Star* :star2:\n\n"
                    "These Christmas Sports don’t test your physical ability, but your **memory, "
                    "thinking skills, and overall capability**. And what’s fun without a little luck? "
                    "Some of these sports will also **test your luck!** :four_leaf_clover:\n\n"
                ),
                color=discord.Color.red()
            )
            embed.set_image(url=COVER_URL)
            embed.set_footer(text="Entry Cost: Each Sport Costs 1× Snow Coin")
            await ctx.send(embed=embed, view=GamesView(ctx.author.id))
            return

        # PLAY subcommand
        if subcommand.lower() in ["play", "sts", "dts"]:
            game_name = args.lower() if args else "spot the santa"

            if game_name in ["spot the santa", "sts"]:
                # 🎅 Spot The Santa
                await spot_the_santa(ctx, spot_answer)

            elif game_name in ["dodge the snowball", "dts"]:
                # ❄️ Dodge The Snowball
                await dodge_the_snowball(ctx, dodge)

            elif game_name in ["find the golden star", "fgs", "ftgs"]:
                # ❄️ Dodge The Snowball
                await find_the_star(ctx, find_star)

            else:
                await ctx.send("This game is not yet available 🎄")

            return

        # SOLVE subcommand
        if subcommand.lower() == "solve":
            if not args:
                await ctx.send("❌ You need to provide positions in format: a1,b2,c3,d4,e1")
                return

            # Remove duplicates from user input
            positions = set(pos.strip().upper() for pos in args.split(","))

            if len(positions) != 5:
                await ctx.send("❌ You must provide exactly 5 unique positions.")
                return

            user_id = ctx.author.id
            if user_id not in spot_answer:
                await ctx.send("❌ You don't have an active Spot The Santa game.")
                return

            image_name = spot_answer[user_id]
            correct_positions = set(spot_santa_answers.get(image_name, []))

            # ✅ Count only unique correct positions
            right_count = len(positions & correct_positions)

            # 🎁 Reward tier (cap at 5)
            reward_tier = min(right_count, 5)

            reward_text = ""
            if reward_tier > 0:
                reward = EVENT_REWARDS[reward_tier]
                santa_boxes = reward["santa_box"]
                pokecash = reward["pokecash"]

                # Give rewards
                await event_reward(ctx, user_id, reward_tier)

                reward_text = (
                    f"\n🎁 You received **{santa_boxes}x Santa Box** "
                    f"and **{pokecash} Pokecash**!"
                )

            # Remove user from active game
            del spot_answer[user_id]

            await ctx.send(
                embed=discord.Embed(
                    title="🎅 Spot The Santa — Results",
                    description=f"You got **{right_count}** correct position(s)!{reward_text}",
                    color=discord.Color.green() if right_count > 0 else discord.Color.red()
                )
            )

        if subcommand.lower() == "dodge":
            if not args:
                await ctx.send("❌ Please choose a tile: `1`, `2`, or `3`.")
                return

            try:
                chosen_tile = int(args.strip())
            except ValueError:
                await ctx.send("❌ Invalid choice. Please use `1`, `2`, or `3`.")
                return

            if chosen_tile not in (1, 2, 3):
                await ctx.send("❌ Invalid tile. Choose only `1`, `2`, or `3`.")
                return

            user_id = ctx.author.id

            if user_id not in dodge:
                await ctx.send("❌ You don't have an active **Dodge the Snowball** game.")
                return

            attack_tile = dodge[user_id]

            chosen_emoji = TILE_EMOJIS[chosen_tile]
            attack_emoji = TILE_EMOJIS[attack_tile]

            # ❌ BAD LUCK — HIT
            if chosen_tile == attack_tile:
                await event_reward(ctx, user_id, 6)

                description = (
                    f"You chose Tile {chosen_emoji}.\n\n"
                    f"**BAD LUCK 😣!** Santa shot Tile {attack_emoji}.\n\n"
                    f"💰 You received **500 Pokecash** for the effort!"
                )

                color = discord.Color.red()

            # ✅ LUCKY — DODGED
            else:
                await event_reward(ctx, user_id, 7)

                description = (
                    f"You chose Tile {chosen_emoji}.\n\n"
                    f"**LUCKY YOU 🍀!** Santa shot Tile {attack_emoji}.\n\n"
                    f"🎁 You received **2x Santa Box** and **1000 Pokecash**!"
                )

                color = discord.Color.green()

            # Cleanup game state
            del dodge[user_id]

            await ctx.send(
                embed=discord.Embed(
                    title="❄️ Dodge the Snowball — Result",
                    description=description,
                    color=color
                )
            )

            return


async def setup(bot):
    await bot.add_cog(ChristmasEvent(bot))






