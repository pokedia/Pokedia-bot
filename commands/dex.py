import discord
from discord.ext import commands
import json
import os
from utils.susp_check import is_not_suspended

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT_DIR, "../simple_pokedex.json"), encoding="utf-8") as f:
    pokedex = json.load(f)

with open(os.path.join(ROOT_DIR, "../spawn_rarity.json"), encoding="utf-8") as f:
    spawn_data = json.load(f)

with open(os.path.join(ROOT_DIR, "../functions/alias.json"), encoding="utf-8") as f:
    alias_data = json.load(f)

fusionable_names = {
    "mewtwo", "deoxys", "eevee", "marshadow", "mew",
    "chandelure", "gallade", "empoleon", "mawile", "audino"
}

def normalize_name(name: str) -> str:
    return name.lower().replace(" ", "-")

def readable_name(name: str) -> str:
    return name.replace("-", " ").title()

def is_catchable(form_name: str) -> str:
    for entry in spawn_data:
        if normalize_name(entry.get("pokemon", "")) == normalize_name(form_name):
            return "Yes"
    return "No"

def is_fusionable(form_name: str) -> str:
    base = form_name.split("-")[0].lower()
    return "Yes" if base in fusionable_names else "No"

def get_aliases(form_name: str):
    return alias_data.get(form_name.replace(" ", "-").title(), [])

def get_entries_by_dex_no(dex_no):
    return [p for p in pokedex if p["dex_no"] == dex_no]

def get_entry_by_form_name(form_name):
    return next((p for p in pokedex if p["form_name"] == form_name), None)

def build_embed(entry, shiny=False):
    form_name = entry["form_name"]
    dex_no = entry["dex_no"]
    display_name = readable_name(form_name)

    if shiny:
        display_name = "✨ " + display_name

    description = entry.get("description", "No description available.")
    types = ", ".join(t.title() for t in entry.get("types", [])) or "Unknown"
    region = entry.get("region", "Unknown").title()

    embed = discord.Embed(
        title=f"#{dex_no}\u2002{display_name}",
        description=description,
        color=discord.Color.orange()
    )

    embed.add_field(name="Types", value=types, inline=True)
    embed.add_field(name="Region", value=region, inline=True)
    embed.add_field(name="Catchable", value=is_catchable(form_name), inline=True)

    stats = entry.get("base_stats", {})
    stats_str = "\n".join(
        f"**{'Sp. Atk' if k == 'special-attack' else 'Sp. Def' if k == 'special-defense' else k.replace('-', ' ').title()}:** {v}"
        for k, v in stats.items()
    ) or "Unknown"

    embed.add_field(name="Base Stats", value=stats_str, inline=True)
    embed.add_field(name="Fusionable", value=is_fusionable(form_name), inline=True)

    aliases = get_aliases(form_name)
    embed.add_field(
        name="Aliases",
        value=", ".join(f"`{a}`" for a in aliases) if aliases else "None",
        inline=True
    )

    if shiny:
        image_url = f"https://github.com/pokedia/images/blob/main/pokemon_shiny/{form_name}.png?raw=true$v5"
    else:
        image_url = f"https://github.com/pokedia/images/blob/main/pokemon_images/{form_name}.png?raw=true&v=4"

    embed.set_image(url=image_url)
    return embed


class DexView(discord.ui.View):
    def __init__(self, current_form_name, is_shiny=False):
        super().__init__(timeout=180)

        self.current_form_name = current_form_name
        self.is_shiny = is_shiny

        entry = get_entry_by_form_name(current_form_name)
        self.current_dex_no = entry["dex_no"] if entry else None

        # ✅ FIX: forms based ONLY on dex_no
        self.forms = get_entries_by_dex_no(self.current_dex_no) if self.current_dex_no else []

        self.previous_button = discord.ui.Button(label="⏮️", style=discord.ButtonStyle.primary)
        self.shiny_button = discord.ui.Button(label="✨", style=discord.ButtonStyle.success)
        self.next_button = discord.ui.Button(label="⏭️", style=discord.ButtonStyle.primary)

        self.previous_button.callback = self.previous_button_callback
        self.shiny_button.callback = self.shiny_button_callback
        self.next_button.callback = self.next_button_callback

        self.add_item(self.previous_button)
        self.add_item(self.shiny_button)
        self.add_item(self.next_button)

        if len(self.forms) > 1:
            self.add_item(self.FormSelect(self.forms, self.current_form_name))

    async def update_message(self, interaction):
        entry = get_entry_by_form_name(self.current_form_name)
        embed = build_embed(entry, shiny=self.is_shiny)

        if not interaction.response.is_done():
            await interaction.response.defer()

        await interaction.edit_original_response(embed=embed, view=self)

    async def previous_button_callback(self, interaction):
        self.current_dex_no -= 1
        while self.current_dex_no > 0 and not get_entries_by_dex_no(self.current_dex_no):
            self.current_dex_no -= 1

        self.forms = get_entries_by_dex_no(self.current_dex_no)
        self.current_form_name = self.forms[0]["form_name"]
        self.is_shiny = False
        await self.update_message(interaction)

    async def shiny_button_callback(self, interaction):
        self.is_shiny = not self.is_shiny
        await self.update_message(interaction)

    async def next_button_callback(self, interaction):
        self.current_dex_no += 1
        while not get_entries_by_dex_no(self.current_dex_no):
            self.current_dex_no += 1

        self.forms = get_entries_by_dex_no(self.current_dex_no)
        self.current_form_name = self.forms[0]["form_name"]
        self.is_shiny = False
        await self.update_message(interaction)

    class FormSelect(discord.ui.Select):
        def __init__(self, forms, current_form_name):
            options = [
                discord.SelectOption(
                    label=readable_name(f["form_name"]),
                    value=f["form_name"],
                    default=(f["form_name"] == current_form_name)
                )
                for f in forms
            ]
            super().__init__(placeholder="Select a form", options=options)

        async def callback(self, interaction):
            self.view.current_form_name = self.values[0]
            self.view.is_shiny = False
            await self.view.update_message(interaction)


class Dex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dex", aliases=["d"])
    @is_not_suspended()
    async def dex_command(self, ctx, *, pokemon_name: str):
        query = normalize_name(pokemon_name)

        entry = get_entry_by_form_name(query)

        if not entry:
            for actual, aliases in alias_data.items():
                if query in [normalize_name(a) for a in aliases]:
                    entry = get_entry_by_form_name(normalize_name(actual))
                    break

        if not entry:
            await ctx.send("Pokémon not found.")
            return

        embed = build_embed(entry)
        view = DexView(entry["form_name"])
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Dex(bot))




