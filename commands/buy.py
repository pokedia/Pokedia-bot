import discord
from discord.ext import commands, tasks
import asyncpg
from datetime import datetime, timezone
from utils.susp_check import is_not_suspended


class ConfirmView(discord.ui.View):
    def __init__(self, ctx, action, amount, total_cost, user_id, pokecash, shards, bot):
        super().__init__()
        self.ctx = ctx
        self.action = action
        self.amount = amount
        self.total_cost = total_cost
        self.user_id = user_id
        self.pokecash = pokecash
        self.shards = shards
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your purchase.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all_buttons()

        async with self.bot.db.pool.acquire() as conn:
            # Fetch current user's pokecash and shards before proceeding
            user_data = await conn.fetchrow("""
                SELECT pokecash, shards FROM users WHERE userid = $1
            """, self.user_id)

            if user_data is None:
                await interaction.response.send_message("User not found.", ephemeral=True)
                return

            current_pokecash = user_data['pokecash']
            current_shards = user_data['shards']

            if self.action == 'shards':
                if current_pokecash < self.total_cost:
                    await interaction.response.send_message("You don't have enough Pokecash.", ephemeral=True)
                else:
                    await conn.execute("""
                        UPDATE users
                        SET pokecash = pokecash - $1,
                            shards = shards + $2
                        WHERE userid = $3
                    """, self.total_cost, self.amount, self.user_id)
                    await interaction.response.send_message(
                        f"Successfully bought {self.amount} shards for {self.total_cost} Pokecash!"
                    )

            elif self.action == 'redeems':
                if current_shards < self.total_cost:
                    await interaction.response.send_message("You don't have enough Shards.", ephemeral=True)
                else:
                    await conn.execute("""
                        UPDATE users
                        SET shards = shards - $1,
                            redeems = redeems + $2
                        WHERE userid = $3
                    """, self.total_cost, self.amount, self.user_id)
                    await interaction.response.send_message(
                        f"Successfully bought {self.amount} redeems for {self.total_cost} Shards!"
                    )

            elif self.action == 'shinycharm':
                if current_shards < self.total_cost:
                    await interaction.response.send_message("You don't have enough Shards.", ephemeral=True)
                else:
                    await conn.execute("""
                        UPDATE users
                        SET shards = shards - $1,
                            shinycharm = TRUE,
                            timer = NOW() + INTERVAL '7 days'
                        WHERE userid = $2
                    """, self.total_cost, self.user_id)
                    await interaction.response.send_message(
                        "✅ You successfully bought a **Shiny Charm** for 150 Shards!"
                    )

        await interaction.message.edit(view=self)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all_buttons()
        await interaction.response.send_message("Purchase canceled.", ephemeral=True)
        await interaction.message.edit(view=self)

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True


class Buy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shinycharm_expiry_task.start()

    def cog_unload(self):
        self.shinycharm_expiry_task.cancel()

    @commands.command()
    @is_not_suspended()
    async def buy(self, ctx, action: str, amount: int = 1):
        action = action.lower()

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot buy an item during trade.")
            return

        if action not in ['shards', 'redeems', 'shinycharm']:
            return await ctx.send("Invalid action. You can only buy `shards`, `redeems`, or `shinycharm`.")

        async with self.bot.db.pool.acquire() as conn:
            user_id = ctx.author.id
            user_data = await conn.fetchrow("""
                SELECT pokecash, shards, redeems, shinycharm FROM users WHERE userid = $1
            """, user_id)

            if not user_data:
                return await ctx.send("You don't have an account yet. Please register first.")

            pokecash, shards, redeems, shinycharm = user_data

            if action == 'shinycharm':
                total_cost = 150
                if shinycharm:
                    return await ctx.send("⚠️ You already have an active Shiny Charm.")
                if shards < total_cost:
                    return await ctx.send(f"❌ Not enough Shards. You need `{total_cost - shards}` more.")
                view = ConfirmView(ctx, action, 1, total_cost, user_id, pokecash, shards, self.bot)
                return await ctx.send(
                    f"✅ Are you sure you want to buy a **Shiny Charm** for `150 Shards`?",
                    view=view
                )

            if amount <= 0:
                return await ctx.send("❌ You cannot buy zero or negative amounts. Enter a positive number.")

            total_cost = amount * 200
            if action == 'shards' and pokecash < total_cost:
                return await ctx.send(f"❌ Not enough Pokecash. You need `{total_cost - pokecash}` more.")
            if action == 'redeems' and shards < total_cost:
                return await ctx.send(f"❌ Not enough Shards. You need `{total_cost - shards}` more.")

            view = ConfirmView(ctx, action, amount, total_cost, user_id, pokecash, shards, self.bot)
            await ctx.send(
                f"✅ Are you sure you want to buy `{amount}` **{action}** for `{total_cost}` "
                f"{'Pokecash' if action == 'shards' else 'Shards'}?",
                view=view
            )

    @tasks.loop(minutes=1)
    async def shinycharm_expiry_task(self):
        async with self.bot.db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT userid, timer FROM users 
                WHERE shinycharm = TRUE AND timer IS NOT NULL AND timer <= NOW()
            """)
            for row in rows:
                userid = row['userid']
                await conn.execute("""
                    UPDATE users
                    SET shinycharm = FALSE,
                        timer = NULL
                    WHERE userid = $1
                """, userid)
                try:
                    user = await self.bot.fetch_user(userid)
                    await user.send("🪙 Your **Shiny Charm** has expired.")
                except discord.Forbidden:
                    pass


async def setup(bot):
    await bot.add_cog(Buy(bot))
