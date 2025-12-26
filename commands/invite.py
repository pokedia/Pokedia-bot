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

        # Skip if member is pending (onboarding)
        if getattr(member, "pending", False):
            print(f"⚠️ Member {member.name} is pending. Skipping invite detection.")
            return

        # Wait a bit more for Discord to update invite uses
        await asyncio.sleep(5)

        invites = await member.guild.invites()
        inviter = None
        max_diff = 0

        for invite in invites:
            old_uses = self.join_snapshot.get(invite.code, 0)
            diff = invite.uses - old_uses
            if diff > max_diff:
                max_diff = diff
                inviter = invite.inviter

        if inviter:
            print(f"🎉 Inviter detected: {inviter}")
        else:
            print(f"⚠️ Could not detect inviter for {member.name}")


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))





