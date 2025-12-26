import discord
import asyncio
from discord.ext import commands, tasks

GUILD_ID = 1339192279470178375  # Your server ID
GIFT_REWARD = 5  # Tip Boxes per invite


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Two caches: live invites & snapshot for joins
        self.live_invites = {}
        self.join_snapshot = {}

        # Start polling invites
        self.invite_poll.start()

    def cog_unload(self):
        self.invite_poll.cancel()

    # Poll invites every 2 seconds to keep cache live
    @tasks.loop(seconds=2)
    async def invite_poll(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        try:
            invites = await guild.invites()
            self.live_invites = {i.code: i.uses for i in invites}
            # Debug print
            print("✅ Cached invites:", self.live_invites)
        except discord.Forbidden:
            print("❌ Missing Manage Server permission.")
        except Exception as e:
            print("❌ Invite poll error:", e)

    @invite_poll.before_loop
    async def before_invite_poll(self):
        await self.bot.wait_until_ready()
        print("✅ Invite polling started")
        # Initial fetch
        await asyncio.sleep(2)
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            invites = await guild.invites()
            self.live_invites = {i.code: i.uses for i in invites}
            print("Initial invite cache:", self.live_invites)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != GUILD_ID:
            return

        # Freeze snapshot BEFORE Discord increments uses
        self.join_snapshot = self.live_invites.copy()

        # Let Discord update invite uses
        await asyncio.sleep(2)

        try:
            invites = await member.guild.invites()
        except discord.Forbidden:
            print("❌ Missing permission to fetch invites.")
            return

        inviter = None
        max_diff = 0

        # Compare against snapshot
        for invite in invites:
            old_uses = self.join_snapshot.get(invite.code, 0)
            diff = invite.uses - old_uses
            if diff > max_diff:
                max_diff = diff
                inviter = invite.inviter

        # Update live cache
        self.live_invites = {i.code: i.uses for i in invites}

        if not inviter:
            print(f"⚠️ Inviter not found for {member.name}. Could be vanity URL or expired invite.")
            return

        print(f"🎉 Inviter detected: {inviter}")

        # Ensure inviter exists in users table
        await self.bot.db.execute(
            """
            INSERT INTO users (userid)
            VALUES ($1)
            ON CONFLICT (userid) DO NOTHING
            """,
            inviter.id
        )

        # Reward Tip/Snow Box
        await self.bot.db.execute(
            """
            INSERT INTO inventory (userid, item_name, value)
            VALUES ($1, 'Snow Box', $2)
            ON CONFLICT (userid, item_name)
            DO UPDATE SET value = inventory.value + $2
            """,
            inviter.id, GIFT_REWARD
        )

        # DM inviter
        try:
            await inviter.send(
                f"🎉 You invited **{member.name}** and received ☃️ **{GIFT_REWARD} Snow Boxes**!"
            )
        except discord.Forbidden:
            print(f"⚠️ Could not DM {inviter} (DMs closed).")


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))




