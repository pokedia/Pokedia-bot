import discord
import asyncio
from discord.ext import commands, tasks

GUILD_ID = 1339192279470178375
GIFT_REWARD = 5


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Live invite cache
        self.invite_cache = {}

        # Start polling
        self.invite_poll.start()

    def cog_unload(self):
        self.invite_poll.cancel()

    # 🔄 Poll invites every 10 seconds
    @tasks.loop(seconds=10)
    async def invite_poll(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        try:
            invites = await guild.invites()
            self.invite_cache = {i.code: i.uses for i in invites}
            print("Cached invites:", self.invite_cache)
        except discord.Forbidden:
            print("❌ Missing Manage Server permission.")
        except Exception as e:
            print("❌ Invite poll error:", e)

    @invite_poll.before_loop
    async def before_invite_poll(self):
        await self.bot.wait_until_ready()
        print("✅ Invite polling started")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != GUILD_ID:
            return

        # 🧊 Snapshot BEFORE Discord updates uses
        before = self.invite_cache.copy()

        # ⏳ Allow Discord to increment uses
        await asyncio.sleep(2)

        try:
            invites = await member.guild.invites()
        except discord.Forbidden:
            print("❌ Missing permission to fetch invites.")
            return

        inviter = None
        max_diff = 0

        for invite in invites:
            old_uses = before.get(invite.code, 0)
            diff = invite.uses - old_uses

            if diff > max_diff:
                max_diff = diff
                inviter = invite.inviter

        # Update cache
        self.invite_cache = {i.code: i.uses for i in invites}

        if not inviter:
            print("⚠️ Could not detect inviter.")
            return

        print(f"🎉 Inviter detected: {inviter}")

        # Ensure inviter exists
        await self.bot.db.execute(
            """
            INSERT INTO users (userid)
            VALUES ($1)
            ON CONFLICT (userid) DO NOTHING
            """,
            inviter.id
        )

        # Reward
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
                f"🎉 **Invite Reward!**\n"
                f"You invited **{member.name}** and received ☃️ **{GIFT_REWARD} Snow Boxes**!"
            )
        except discord.Forbidden:
            print("⚠️ DMs closed.")


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))




