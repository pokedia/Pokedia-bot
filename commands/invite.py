import discord
import asyncio
from discord.ext import commands, tasks

GUILD_ID = 1339192279470178375
GIFT_REWARD = 5  # Snow Boxes per invite


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # 🔥 Live cache updated every 2 seconds
        self.live_invites: dict[str, int] = {}

        # 🧊 Snapshot taken at join time
        self.join_snapshot: dict[str, int] = {}

        self.invite_poll.start()

    def cog_unload(self):
        self.invite_poll.cancel()

    # -------------------- INVITE POLLER --------------------
    @tasks.loop(seconds=2)
    async def invite_poll(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        try:
            invites = await guild.invites()
            self.live_invites = {i.code: i.uses for i in invites}
            print("Cached invites:", self.live_invites)
        except discord.Forbidden:
            print("❌ Missing Manage Server permission.")
        except Exception as e:
            print("❌ Invite poll error:", e)

    @invite_poll.before_loop
    async def before_invite_poll(self):
        await self.bot.wait_until_ready()
        print("✅ Invite polling started")

    # -------------------- MEMBER JOIN --------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return

        # 🧊 Freeze snapshot BEFORE Discord updates uses
        self.join_snapshot = self.live_invites.copy()

        # ⏳ Allow Discord to increment invite uses
        await asyncio.sleep(2)

        try:
            invites = await member.guild.invites()
        except discord.Forbidden:
            return

        inviter = None
        highest_diff = 0

        # 🔍 Compare snapshot vs current
        for invite in invites:
            before = self.join_snapshot.get(invite.code, 0)
            diff = invite.uses - before

            if diff > highest_diff:
                highest_diff = diff
                inviter = invite.inviter

        if not inviter:
            print("⚠️ Inviter not found (vanity / onboarding / deleted invite).")
            return

        print(f"🎉 Inviter detected: {inviter} for {member}")

        # -------------------- DATABASE --------------------

        # 🔒 Ensure user exists
        await self.bot.db.execute(
            """
            INSERT INTO users (userid)
            VALUES ($1)
            ON CONFLICT (userid) DO NOTHING
            """,
            inviter.id
        )

        # 📦 Give Snow Boxes
        await self.bot.db.execute(
            """
            INSERT INTO inventory (userid, item_name, value)
            VALUES ($1, 'Snow Box', $2)
            ON CONFLICT (userid, item_name)
            DO UPDATE SET value = inventory.value + EXCLUDED.value
            """,
            inviter.id,
            GIFT_REWARD
        )

        # -------------------- DM --------------------
        try:
            await inviter.send(
                f"🎉 You invited **{member.name}**!\n"
                f"☃️ You received **{GIFT_REWARD} Snow Boxes**."
            )
        except discord.Forbidden:
            print(f"⚠️ Could not DM {inviter} (DMs closed).")


# -------------------- SETUP --------------------
async def setup(bot):
    await bot.add_cog(InviteTracker(bot))




