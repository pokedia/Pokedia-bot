import discord
import asyncio
from discord.ext import commands, tasks

GUILD_ID = 1339192279470178375  # 🔴 CHANGE if needed
GIFT_REWARD = 5  # Snow Boxes per invite


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}
        self.invite_poll.start()

    def cog_unload(self):
        self.invite_poll.cancel()

    # 🔄 Poll invites every 2 seconds so new links are never missed
    @tasks.loop(seconds=2)
    async def invite_poll(self):
        await self.fetch_invites()

    @invite_poll.before_loop
    async def before_invite_poll(self):
        await self.bot.wait_until_ready()
        await self.fetch_invites()
        print("✅ Invite polling started (every 2 seconds)")

    async def fetch_invites(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        try:
            invites = await guild.invites()
            self.invites = {invite.code: invite.uses for invite in invites}
            print("✅ Cached invites:", self.invites)
        except discord.Forbidden:
            print("❌ Missing Manage Server permission.")
        except Exception as e:
            print("❌ Invite fetch error:", e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != GUILD_ID:
            return

        # ⏳ Let Discord update invite uses
        await asyncio.sleep(2)

        try:
            invites = await member.guild.invites()
        except discord.Forbidden:
            print("❌ Cannot fetch invites (permission).")
            return

        print("OLD INVITES:", self.invites)

        inviter = None
        max_diff = 0

        # 🔍 DELTA-BASED detection (THIS IS THE FIX)
        for invite in invites:
            old_uses = self.invites.get(invite.code, 0)
            diff = invite.uses - old_uses

            if diff > max_diff:
                max_diff = diff
                inviter = invite.inviter

        # 🔁 Update cache AFTER detection
        self.invites = {invite.code: invite.uses for invite in invites}

        if not inviter:
            print("⚠️ Inviter not found (vanity / already cached join).")
            return

        print(f"🎉 Inviter detected: {inviter} → +{GIFT_REWARD} Snow Boxes")

        # 🔒 Ensure inviter exists
        await self.bot.db.execute(
            """
            INSERT INTO users (userid)
            VALUES ($1)
            ON CONFLICT (userid) DO NOTHING
            """,
            inviter.id
        )

        # 📦 Reward Snow Box
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



