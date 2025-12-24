import discord
from discord.ext import commands

class HelpView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0

    async def update_message(self, interaction: discord.Interaction):
        """Update the embed message with the current page."""
        embed = self.embeds[self.current_page]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page."""
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await self.update_message(interaction)

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Sends a paginated help embed."""
        embeds = [
            discord.Embed(title="Help - Page 1", description="**Basic Commands**", color=discord.Color.blue())
            .add_field(name="`start`", value="• Start your journey.", inline=False)
            .add_field(name="`pick`", value="• Check your items.", inline=False)
            .add_field(name="`pokemon or !p`", value="• Shows your pokemon inventory", inline=False)
            .add_field(name="`inventory or !inv`", value="• Shows your item inventory", inline=False)
            .add_field(name="`balance or !bal`", value="• Shows your pokecash and shards balance.", inline=False)
            .add_field(name="`catch <name> or !c`", value="• Lets you catch pokemon", inline=False)
            .add_field(name="`favorite <id> or !fav`", value="• Favorites a pokemon", inline=False)
            .add_field(name="`favorite_all [filters] or !fa`", value="• Favorites a group of pokemons", inline=False)
            .add_field(name="`release <id>`", value="• Releases Pokemon.", inline=False),

            discord.Embed(title="Help - Page 2", description="**Market Commands**", color=discord.Color.blue())
            .add_field(name="`market_search or !ms`", value="• View Pokemon's available in market ", inline=False)
            .add_field(name="`market_add <id> <price> or !ma`", value="• Add your pokemon to market", inline=False)
            .add_field(name="`market_buy <marketid> or !mb`", value="• Buy pokemon from the market", inline=False)
            .add_field(name="`market_info <marketid> or !mi`", value="• Shows stats of a market pokemon", inline=False)
            .add_field(name="`market_toggle True/False or !mt`", value="• Allow/Disallow market dm's & offers", inline=False)
            .add_field(name="`market_dm <marketid> <message> or !md`", value="• Dm's the owner of the market listing with your message", inline=False)
            .add_field(name="`market_offer <marketid> <price> or !mo`", value="• Sends your offer for the pokemon to the owner", inline=False),

            discord.Embed(title="Help - Page 3", description="**Trading Commands**", color=discord.Color.blue())
            .add_field(name="`trade <@user> or !t`", value="• Sends Trade request to the respective user", inline=False)
            .add_field(name="`trade_add <id> or !ta`", value="• Adds that specific pokemon to the trade", inline=False)
            .add_field(name="`trade_adall [filters] or !taa`", value="• Adds all pokemon with matching criteria in the trade", inline=False)
            .add_field(name="`trade_confirm or !tc`", value="• Confirms the trade status from your side.", inline=False)
            .add_field(name="`trade_cancel or !tx`", value="• Cancels the ongoing trade.", inline=False),

            discord.Embed(title="Help - Page 4", description="**Incense Commands**", color=discord.Color.blue())
            .add_field(name="`incense buy <time> <interval>`", value="• Starts a Incense in the specific channel.", inline=False)
            .add_field(name="`incensepause or !ip`", value="• Pause your channels running Incense.", inline=False)
            .add_field(name="`incenseresume or !ir`",  value="• Resumes your channels paused Incense", inline=False),

            discord.Embed(title="Help - Page 5", description="**Shop Commands**", color=discord.Color.blue())
            .add_field(name="`shop`", value="• Shows Shop Interface.", inline=False)
            .add_field(name="`buy shards/redeems <amt> /shinycharm`", value="• Lets you Shards and Redeems", inline=False),

            discord.Embed(title="Help - Page 6", description="**Fusion Commands**", color=discord.Color.blue())
            .add_field(name="`fuse add <ID> <ID>`", value="• Adds Pokemon Pairs to Fusion Incubator.", inline=False)
            .add_field(name="`fuse remove`", value="• Removes the pair from the incubator.", inline=False)
            .add_field(name="`fuse start`", value="• Starts the fusion process.", inline=False)
            .add_field(name="`fuse`", value="• Shows your Fusion Incubator..", inline=False),

            discord.Embed(title="Help - Page 7", description="**Filters Commands**", color=discord.Color.blue())
            .add_field(name="`--n or --name`", value="• Filters Name.", inline=False)
            .add_field(name="`--iv ><{iv}`", value="• Filters IV.", inline=False)
            .add_field(name="`--shiny or --sh`", value="• Filters Shinies.", inline=False)
            .add_field(name="`--fusionable or --fn`", value="• Filters Fusionable Pokemon.", inline=False)
            .add_field(name="`--{stat} [IV]`", value="• Filters Pokemons with that STAT IV.", inline=False)
            .add_field(name="`--rare or --ra`", value="• Filters every Rare Pokemon.", inline=False)
            .add_field(name="`--legendary or --leg`", value="• Filters every Legendary Pokemon", inline=False)
            .add_field(name="`--mythical or --my`", value="• Filters every Mythical Pokemon.", inline=False)
            .add_field(name="`--ultrabeast or --ub`", value="• Filters every Ultrabeast Pokemon.", inline=False)
            .add_field(name="`--event or --ev`", value="• Filters Event Pokemons.", inline=False)
            .add_field(name="`--limit or --lim`", value="• Filters Pokemons to that certain limit.", inline=False)
            .add_field(name="`--skip or --sk`", value="• Filters Pokemons after certain limit", inline=False)
        ]

        view = HelpView(embeds)
        await ctx.send(embed=embeds[0], view=view)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
