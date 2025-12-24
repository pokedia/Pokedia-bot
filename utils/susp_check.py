import discord
from discord.ext import commands


def build_suspension_embed(reason: str) -> discord.Embed:
    embed = discord.Embed(
        title="🚫 User Suspension",
        description=(
            "Your access to Pokedia commands has been restricted.\n\n"
            "Failure to comply with Pokedia rules, policies, or guidelines may lead "
            "to long-term or permanent suspension. We expect all users to follow the "
            "rules to maintain a fair and respectful environment."
        ),
        color=discord.Color.red()
    )

    embed.add_field(
        name="📄 Suspension Reason",
        value=reason or "No reason provided.",
        inline=False
    )

    embed.add_field(
        name="📩 Apply For Unsuspension",
        value=(
            "If you believe this suspension is invalid or unrelated to your actions, "
            "you may appeal the decision.\n\n"
            "Please create a ticket in the **original Pokedia server** under "
            "**#suspension-appeal** and clearly explain your situation."
        ),
        inline=False
    )

    embed.set_footer(text="Pokedia Moderation System")

    return embed


def is_not_suspended():
    async def predicate(ctx: commands.Context) -> bool:
        # asyncpg fetchrow returns Record or None
        row = await ctx.bot.db.fetchrow(
            "SELECT suspended, reason FROM users WHERE userid = $1",
            ctx.author.id
        )

        # User exists and is suspended
        if row and row["suspended"]:
            embed = build_suspension_embed(row["reason"])
            await ctx.send(embed=embed)
            return False  # ❌ block command

        return True  # ✅ allow command

    return commands.check(predicate)
