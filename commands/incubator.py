import discord
from discord.ext import commands
from collections import defaultdict

class Incubator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_counts = {}

    @commands.command(aliases=["egg"])
    async def incubator(self, ctx):
        user_id = ctx.author.id
        username = ctx.author.display_name

        # Fetch incubator row for the user
        incubator_data = await self.bot.db.fetchrow("SELECT xp, total_xp, queue FROM incubator WHERE ownerid = $1", user_id)

        if incubator_data:
            egg_xp = incubator_data["xp"]
            egg_total_xp = incubator_data["total_xp"]
            queue = incubator_data["queue"]
        else:
            egg_xp = 0
            egg_total_xp = 0
            queue = 0

        embed = discord.Embed(
            title=f"{username}'s Egg Incubator",
            description=(
                "You can obtain Eggs while catching, which will automatically be added "
                "in the incubator or in queue.\n\n"
                "Eggs incubate and hatch to birth an off-spring of a pokemon species, whereas "
                "in some cases the incubation period fall shorts by time and thus a Baby Pokemon is born. "
                "According to Pokedia scientists there is 20% Chance for a Baby Pokemon to be born\n\n"
                f"**Your Egg:** {egg_xp}/{egg_total_xp}"
            ),
            color=discord.Color.purple()
        )
        embed.set_image(url="https://raw.githubusercontent.com/pokedia/images/main/extras/incubator.png")

        view = self.IncubatorView(self.bot, user_id, egg_xp, egg_total_xp, queue)
        await ctx.send(embed=embed, view=view)

    message_counter = defaultdict(int)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # Ignore messages from bots
            return

        user_id = message.author.id

        # Initialize message count if it doesn't exist
        if user_id not in self.message_counts:
            self.message_counts[user_id] = 0

        # Increment the message count
        self.message_counts[user_id] += 1

        # Add XP every 2 messages
        if self.message_counts[user_id] % 4 == 0:
            # Only update XP if the user exists in the database
            await self.add_xp_to_user(user_id, 5)  # Add 5 XP to the user

    async def add_xp_to_user(self, user_id, xp_to_add):
        # Check if user already exists in the database
        query = """
            SELECT xp FROM incubator WHERE ownerid = $1
        """
        result = await self.bot.db.fetchrow(query, user_id)

        if result:
            # User exists, update their XP
            current_xp = result['xp']
            await self.bot.db.execute("""
                UPDATE incubator
                SET xp = $1
                WHERE ownerid = $2
            """, current_xp + xp_to_add, user_id)

    class IncubatorView(discord.ui.View):
        def __init__(self, bot, user_id, egg_xp, egg_total_xp, queue):
            super().__init__(timeout=None)
            self.bot = bot
            self.user_id = user_id
            self.egg_xp = egg_xp
            self.egg_total_xp = egg_total_xp
            self.queue = queue  # ✅ Add this

        @discord.ui.button(label="Queue", style=discord.ButtonStyle.success)
        async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Your Egg Queue",
                description=(
                    "Catching Eggs while one is already Incubating, will add the Eggs to Queue. "
                    "After Incubating is over your queue eggs start incubating.\n\n"
                    f"**Egg's Queue:** {self.queue}"
                ),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label="View Stats", style=discord.ButtonStyle.blurple)
        async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't use this button!", ephemeral=True)
                return

            # Fetch incubator data for the user from the database
            query = """
                SELECT hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv, total_iv_percentage
                FROM incubator WHERE ownerid = $1
            """
            incubator_data = await self.bot.db.fetchrow(query, self.user_id)

            if not incubator_data:
                await interaction.response.send_message("No incubator data found.", ephemeral=True)
                return

            # Calculate XP percentage completion
            xp_percentage = (self.egg_xp / self.egg_total_xp) * 100

            # Reveal stat IVs based on XP percentage completion
            hp_iv = incubator_data["hp_iv"] if xp_percentage >= 15 else "???"
            attack_iv = incubator_data["attack_iv"] if xp_percentage >= 30 else "???"
            defense_iv = incubator_data["defense_iv"] if xp_percentage >= 45 else "???"
            spatk_iv = incubator_data["spatk_iv"] if xp_percentage >= 60 else "???"
            spdef_iv = incubator_data["spdef_iv"] if xp_percentage >= 75 else "???"
            speed_iv = incubator_data["speed_iv"] if xp_percentage >= 90 else "???"
            total_iv_percentage = incubator_data["total_iv_percentage"] if xp_percentage >= 95 else "???"

            # Embed message with dynamic stat reveal
            embed = discord.Embed(
                title="Level 1 ???",
                description=None,
                color=discord.Color.blue()
            )
            embed.add_field(name="XP:", value=f"{self.egg_xp}/{self.egg_total_xp}", inline=True)
            embed.add_field(
                name="Stats",
                value=(
                    f"**HP**: ??? - IV {hp_iv}/31\n"
                    f"**Attack**: ??? - IV {attack_iv}/31\n"
                    f"**Defense**: ??? - IV {defense_iv}/31\n"
                    f"**Sp. Atk**: ??? - IV {spatk_iv}/31\n"
                    f"**Sp. Def**: ??? - IV {spdef_iv}/31\n"
                    f"**Speed**: ??? - IV {speed_iv}/31\n"
                    f"**Total IV**: {total_iv_percentage}%"
                ),
                inline=False
            )
            embed.set_footer(text="Your egg is still hatching...")

            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Incubator(bot))


