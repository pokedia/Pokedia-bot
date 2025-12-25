import discord
from discord.ext import commands

GUILD_ID = 1328824772066279554  # Your server ID
GIFT_REWARD = 3  # Number of gift boxes per invite


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_invites(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            self.bot.invites = {invite.code: invite.uses for invite in await guild.invites()}
        print("Fetched and stored invites:", self.bot.invites)

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ InviteTracker Cog loaded.")
        self.bot.invites = {}
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await self.fetch_invites()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != GUILD_ID:
            return

        if not hasattr(self.bot, "invites") or not self.bot.invites:
            await self.fetch_invites()

        invites = await member.guild.invites()
        new_invites = {invite.code: invite.uses for invite in invites}
        inviter = None

        for code, uses in new_invites.items():
            if code in self.bot.invites and uses > self.bot.invites[code]:
                invite = discord.utils.get(invites, code=code)
                inviter = invite.inviter
                break

        self.bot.invites = new_invites

        if not inviter:
            return

        # 🔒 SUSPENSION CHECK — silently block suspended users
        suspended = await self.bot.db.fetchval(
            "SELECT suspended FROM users WHERE userid = $1",
            inviter.id
        )

        if suspended:
            return  # ❌ No reward, no message, nothing

        # 🎁 Give reward to unsuspended inviter
        row = await self.bot.db.fetchrow(
            "SELECT value FROM inventory WHERE userid = $1 AND item_name = 'Snow Box'",
            inviter.id
        )

        if row:
            await self.bot.db.execute(
                "UPDATE inventory SET value = value + $1 WHERE userid = $2 AND item_name = 'Snow Box'",
                GIFT_REWARD, inviter.id
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO inventory (userid, item_name, value) VALUES ($1, 'Snow Box', $2)",
                inviter.id, GIFT_REWARD
            )

        try:
            await inviter.send(
                f"You invited {member.name} and received 🎁 {GIFT_REWARD} Snow boxes!"
            )
        except discord.Forbidden:
            pass  # Silently ignore DM failures


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))

