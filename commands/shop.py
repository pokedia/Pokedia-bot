import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.susp_check import is_not_suspended

class ShopView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your shop session.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Page 1", style=discord.ButtonStyle.primary)
    async def page_1(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="Pokedia Shard Store",
            description="What are you looking for?",
            color=discord.Color.blue()
        )
        embed.add_field(name="**Shards:**", value="200 Pokecash Each.", inline=False)
        embed.add_field(name="**Redeems:**", value="200 Shards Each.", inline=False)
        embed.add_field(name="**Shiny Charm:**", value="150 Shards Each.", inline=False)
        embed.set_footer(text="To buy use, p!buy shards/redeems <amount> or p!buy shinycharm")
        embed.set_image(url="https://raw.githubusercontent.com/pokedia/images/main/extras/shopkeeper_1.png")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Page 2", style=discord.ButtonStyle.secondary)
    async def page_2(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="Pokedia Incense Store",
            description="Which Incense would you like to buy?",
            color=discord.Color.blue()
        )
        embed.add_field(name="**10's Incense:**", value="1h: 100 Shards; 3h: 300 Shards", inline=False)
        embed.add_field(name="**20's Incense:**", value="1h: 50 Shards; 3h: 150 Shards", inline=False)
        embed.add_field(name="**30's Incense:**", value="1h: 30 Shards; 3h: 90 Shards", inline=False)
        embed.set_footer(text="To buy use, !incense buy <time> <seconds>.")
        embed.set_image(url="https://raw.githubusercontent.com/pokedia/images/main/extras/shopkeeper_2.png")
        await interaction.response.edit_message(embed=embed, view=self)

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @is_not_suspended()
    async def shop(self, ctx):
        embed = discord.Embed(
            title="Welcome to the Pokedia Store!",
            description="What would you like to buy?",
            color=discord.Color.blue()
        )
        embed.add_field(name="**Shop 1:**", value="Shards, Redeems, Shiny Charm", inline=False)
        embed.add_field(name="**Shop 2:**", value="Incense's", inline=False)
        embed.set_image(url="https://raw.githubusercontent.com/pokedia/images/main/extras/shopkeeper.png")
        view = ShopView(user_id=ctx.author.id)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Shop(bot))