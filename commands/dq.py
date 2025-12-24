import discord
from discord.ext import commands
from discord.ui import Button, View
import json
from functions.fetch_pokemon import fetch_pokemon_name  # Import the fetch_pokemon_name function
import random
import re
import urllib.parse
import aiocron
import pytz
from utils.susp_check import is_not_suspended

class DailyQuests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        aiocron.crontab('0 12 * * *', func=lambda: self.auto_assign_quests(notify_users=True), start=True, tz=pytz.timezone('UTC'))


    async def auto_assign_quests(self, notify_users=False):
        """Assigns daily quests to all users. If notify_users is True, DMs users."""
        print("🛠️ Automatically assigning daily quests to users...")

        # Load catch quests from JSON
        with open("catch_quests.json", "r") as f:
            quest_data = json.load(f)
        quests = quest_data["catch_quests"]

        # Fetch all users from DB
        users = await self.bot.db.fetch("SELECT userid FROM users")

        for user in users:
            user_id = user["userid"]
            selected = random.sample(quests, 4)

            dq_descriptions = []
            total_targets = []

            for quest in selected:
                if quest.get("specific"):  # If the quest is for a specific Pokémon
                    name = fetch_pokemon_name()
                    description = quest["description"].replace("{name}", name)
                else:
                    description = quest["description"]

                dq_descriptions.append(description)
                total_targets.append(quest["target"])

            while len(total_targets) < 4:
                total_targets.append(0)

            await self.bot.db.execute("""
                UPDATE users
                SET dq1 = $1,
                    dq2 = $2,
                    dq3 = $3,
                    dq4 = $4,
                    totaldq1 = $5,
                    totaldq2 = $6,
                    totaldq3 = $7,
                    totaldq4 = $8,
                    done1 = 0,
                    done2 = 0,
                    done3 = 0,
                    done4 = 0
                WHERE userid = $9
            """, *dq_descriptions, *total_targets, user_id)

            # DM user if it's a scheduled daily reset
            if notify_users:
                user_obj = self.bot.get_user(user_id)
                if user_obj:
                    try:
                        await user_obj.send("📢 Your **Daily Quests** have been reassigned!\nHappy catching! 🎯")
                    except Exception as e:
                        print(f"[DEBUG] Couldn't DM user {user_id}: {e}")

        print("✅ Daily quests assigned to all users.")

    import re

    async def update_daily_quest_progress(self, user_id, caught_name):
        with open("simple_pokedex.json", "r", encoding="utf-8") as f:
            pokedex = json.load(f)

        matched = None
        for pokemon in pokedex:
            if pokemon["form_name"].lower() == caught_name.lower():
                matched = pokemon
                break

        if not matched:
            print(f"[DEBUG] No match found for caught Pokémon: {caught_name}")
            return  # No match found

        # Get the types of the matched Pokémon
        types = [t.lower() for t in matched.get("types", [])]
        print(f"[DEBUG] Pokémon found: {caught_name}, types: {types}")

        # Fetch user quests and pokecash
        user_data = await self.bot.db.fetchrow(
            "SELECT dq1, dq2, dq3, dq4, done1, done2, done3, done4, totaldq1, totaldq2, totaldq3, totaldq4, pokecash FROM users WHERE userid = $1",
            user_id
        )
        if not user_data:
            print(f"[DEBUG] No user data found for user ID {user_id}")
            return

        dq = [user_data["dq1"], user_data["dq2"], user_data["dq3"], user_data["dq4"]]
        done = [user_data["done1"], user_data["done2"], user_data["done3"], user_data["done4"]]
        total = [user_data["totaldq1"], user_data["totaldq2"], user_data["totaldq3"], user_data["totaldq4"]]
        pokecash = user_data["pokecash"]

        updated = False
        completed = []

        for i in range(4):
            quest = dq[i]
            print(f"[DEBUG] Checking quest {i + 1}: {quest}")

            if not quest:
                continue

            # Type-based quests
            if "-type" in quest.lower():
                match = re.search(r"Catch \d+ (\w+)-type", quest, re.IGNORECASE)
                if match:
                    quest_type = match.group(1).lower()
                    print(f"[DEBUG] Quest requires catching a {quest_type}-type Pokémon")
                    if quest_type in types:
                        done[i] += 1
                        updated = True
                        print(f"[DEBUG] Progress updated for type quest {i + 1}")

            # Specific Pokémon name quests
            elif re.search(r"Catch \d+ (\w+)", quest):
                match = re.search(r"Catch \d+ (\w+)", quest)
                if match:
                    quest_name = match.group(1).lower()
                    print(f"[DEBUG] Quest requires catching: {quest_name}")
                    if quest_name == caught_name.lower():
                        done[i] += 1
                        updated = True
                        print(f"[DEBUG] Progress updated for quest {i + 1}")

        # Check for completed quests
        for i in range(4):
            if dq[i] and done[i] >= total[i] and total[i] > 0:
                print(f"[DEBUG] Quest {i + 1} completed!")
                dq[i] = ""
                done[i] = 0
                total[i] = 0
                completed.append(i + 1)

        # Calculate and apply reward
        reward_per_quest = 25000
        reward = reward_per_quest * len(completed)
        new_pokecash = pokecash + reward

        if updated or completed:
            print(f"[DEBUG] Final quest states — done: {done}, dq: {dq}, total: {total}, pokecash: {new_pokecash}")
            await self.bot.db.execute("""
                UPDATE users SET 
                    dq1 = $1, dq2 = $2, dq3 = $3, dq4 = $4,
                    done1 = $5, done2 = $6, done3 = $7, done4 = $8,
                    totaldq1 = $9, totaldq2 = $10, totaldq3 = $11, totaldq4 = $12,
                    pokecash = $13
                WHERE userid = $14
            """, dq[0], dq[1], dq[2], dq[3],
                                      done[0], done[1], done[2], done[3],
                                      total[0], total[1], total[2], total[3],
                                      new_pokecash, user_id)

            # DM the user for each completed quest
            user = self.bot.get_user(user_id)
            if user is not None:
                for quest_num in completed:
                    try:
                        await user.send(
                            f"You have completed your **Daily Quest {quest_num}**! 🎉\nYou received **25,000 Pokécash**!"
                        )
                    except Exception as e:
                        print(f"[DEBUG] Could not DM user {user_id}: {e}")
        else:
            print(f"[DEBUG] No progress to update for user {user_id}")

    @commands.command(name="dq", aliases=["dailyquest"])
    @is_not_suspended()
    async def view_quests(self, ctx):
        """Shows the user's daily quests with pagination."""
        user_id = ctx.author.id
        user_data = await self.bot.db.fetchrow(
            "SELECT dq1, dq2, dq3, dq4, totaldq1, totaldq2, totaldq3, totaldq4, done1, done2, done3, done4 FROM users WHERE userid = $1",
            user_id
        )

        if not user_data:
            await ctx.send("You have no daily quests assigned.")
            return

        dq1, dq2, dq3, dq4, totaldq1, totaldq2, totaldq3, totaldq4, done1, done2, done3, done4 = user_data
        quests = [dq1, dq2, dq3, dq4]
        totals = [totaldq1, totaldq2, totaldq3, totaldq4]
        done = [done1, done2, done3, done4]

        class QuestPagination(View):
            def __init__(self, user_id, quests, done, totals):
                super().__init__(timeout=60)
                self.user_id = user_id
                self.quests = quests
                self.done = done
                self.totals = totals
                self.quest_index = 0

                # Buttons
                prev_button = Button(label="Previous", style=discord.ButtonStyle.primary)
                next_button = Button(label="Next", style=discord.ButtonStyle.primary)

                prev_button.callback = self.previous_callback
                next_button.callback = self.next_callback

                self.add_item(prev_button)
                self.add_item(next_button)

            async def interaction_check(self, interaction: discord.Interaction):
                return interaction.user.id == self.user_id

            async def generate_quest_embed(self, index: int):
                description = self.quests[index]
                image_url = "https://raw.githubusercontent.com/pokedia/images/main/extras/default.png"

                # Category-based (e.g., "Catch 10 Ice-type Pokémon")
                if "type" in description:
                    match = re.search(r"Catch \d+ (\w+)-type", description)
                    if match:
                        category = match.group(1).lower()
                        image_url = f"https://raw.githubusercontent.com/pokedia/images/main/extras/{urllib.parse.quote(category)}.png"

                # Specific Pokémon-based (e.g., "Catch 1 Pikachu")
                elif "Catch" in description:
                    match = re.search(r"Catch \d+ (\w+)", description)
                    if match:
                        pokemon_name = match.group(1).lower()
                        image_url = f"https://raw.githubusercontent.com/pokedia/images/main/pokemon_images/{urllib.parse.quote(pokemon_name)}.png"

                print(f"[DEBUG] Quest {index + 1} → Image URL: {image_url}")

                embed = discord.Embed(
                    title=f"Daily Quest {index + 1}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Description", value=description, inline=False)
                embed.add_field(name="Progress", value=f"{self.done[index]}/{self.totals[index]}", inline=True)
                embed.add_field(name="Reward", value="25,000 Pokécash", inline=True)
                embed.set_thumbnail(url=image_url)

                return embed

            async def previous_callback(self, interaction: discord.Interaction):
                if self.quest_index > 0:
                    self.quest_index -= 1
                    embed = await self.generate_quest_embed(self.quest_index)
                    await interaction.response.edit_message(embed=embed, view=self)

            async def next_callback(self, interaction: discord.Interaction):
                if self.quest_index < len(self.quests) - 1:
                    self.quest_index += 1
                    embed = await self.generate_quest_embed(self.quest_index)
                    await interaction.response.edit_message(embed=embed, view=self)

        view = QuestPagination(user_id, quests, done, totals)
        embed = await view.generate_quest_embed(0)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(DailyQuests(bot))

