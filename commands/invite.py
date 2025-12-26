import discord
import asyncio
from discord.ext import commands

GUILD_ID = 1339192279470178375  # Your server ID
GIFT_REWARD = 5  # Tip Boxes per invite


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.invites = {}

    async def fetch_invites(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            print("❌ Guild not found.")
            return

        try:
            invites = await guild.invites()
            self.bot.invites = {invite.code: invite.uses for invite in invites}
            print("✅ Cached invites:", self.bot.invites)
        except discord.Forbidden:
            print("❌ Missing 'Manage Server' permission for invite tracking.")
        except Exception as e:
            print("❌ Error fetching invites:", e)

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ InviteTracker Cog loaded.")
        await self.fetch_invites()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != GUILD_ID:
            return

        # Allow Discord time to update invite uses
        await asyncio.sleep(2)

        if not self.bot.invites:
            print("⚠️ Invite cache empty. Re-fetching...")
            await self.fetch_invites()
            return

        try:
            invites = await member.guild.invites()
        except discord.Forbidden:
            print("❌ Missing permission to fetch invites.")
            return

        new_invites = {invite.code: invite.uses for invite in invites}

        print("OLD INVITES:", self.bot.invites)
        print("NEW INVITES:", new_invites)

        inviter = None

        for invite in invites:
            if invite.code in self.bot.invites:
                if invite.uses > self.bot.invites[invite.code]:
                    inviter = invite.inviter
                    print(f"🎉 Inviter detected: {inviter}")
                    break

        # Update cache
        self.bot.invites = new_invites

        if not inviter:
            print("⚠️ Could not detect inviter (vanity / expired / cache issue).")
            return

        # 🔒 Ensure inviter exists in users table
        await self.bot.db.execute(
            """
            INSERT INTO users (userid)
            VALUES ($1)
            ON CONFLICT (userid) DO NOTHING
            """,
            inviter.id
        )

        # 📦 Reward Tip Box
        await self.bot.db.execute(
            """
            INSERT INTO inventory (userid, item_name, value)
            VALUES ($1, 'Snow Box', $2)
            ON CONFLICT (userid, item_name)
            DO UPDATE SET value = inventory.value + $2
            """,
            inviter.id, GIFT_REWARD
        )

        # 📩 DM inviter
        try:
            await inviter.send(
                f"🎉 **Invite Reward!**\n"
                f"You invited **{member.name}** and received ☃️ **{GIFT_REWARD} Snow Boxes**!"
            )
        except discord.Forbidden:
            print(f"⚠️ Could not DM {inviter} (DMs closed).")


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))


