import discord
from discord.ext import commands
from math import ceil
from functions.Filters import (
    filter_shiny, filter_name, filter_total_iv, filter_stats,
    filter_limit, filter_skip, filter_rarity,
)
from database import Database
import re
import asyncpg
from discord.ui import  View, Button
from utils.susp_check import is_not_suspended

# Manual rarity mapping
RARE_POKEMON = {
    "legendary": [
        "Articuno", "Zapdos", "Moltres", "Raikou", "Entei", "Suicune",
        "Regirock", "Regice", "Registeel", "Latias", "Latios", "Kyogre",
        "Groudon", "Rayquaza", "Uxie", "Mesprit", "Azelf", "Dialga", "Palkia",
        "Heatran", "Regigigas", "Giratina", "Cresselia", "Cobalion", "Terrakion",
        "Virizion", "Tornadus", "Thundurus", "Reshiram", "Zekrom", "Landorus",
        "Kyurem", "Xerneas", "Yveltal", "Zygarde", "Type: Null", "Silvally",
        "Tapu Koko", "Tapu Lele", "Tapu Bulu", "Tapu Fini", "Cosmog", "Cosmoem",
        "Solgaleo", "Lunala", "Necrozma", "Zacian", "Zamazenta", "Eternatus",
        "Kubfu", "Urshifu", "Regieleki", "Regidrago", "Glastrier", "Spectrier",
        "Calyrex", "Koraidon", "Miraidon", "Ogerpon"
    ],
    "mythical": [
        "Mew", "Celebi", "Jirachi", "Deoxys", "Phione", "Manaphy",
        "Darkrai", "Shaymin", "Arceus", "Victini", "Keldeo",
        "Meloetta", "Genesect", "Diancie", "Hoopa", "Volcanion",
        "Magearna", "Marshadow", "Zeraora", "Meltan", "Melmetal",
        "Zarude", "Enamorus"
    ],
    "ultrabeast": [
        "Nihilego", "Buzzwole", "Pheromosa", "Xurkitree", "Celesteela",
        "Kartana", "Guzzlord", "Poipole", "Naganadel", "Stakataka",
        "Blacephalon"
    ]
}

EVENT_POKEMON = {
    "event": [
        "Boss Squirtle", "Cupcake Swirlix", "Balloons Spheal", "Gifts Vulpix", "Mr Jester", "Waiter Snorlax", "Chef Teddiursa", "Hotchocolate Lotad", "Pikachu Belle", "Pikachu Libre", "Pikachu PhD", "Pikachu Pop Star", "Pikachu Rock Star", "Pikachu Original Cap", "Pikachu Hoenn Cap", "Pikachu Sinnoh Cap", "Pikachu Unova Cap", "Pikachu Kalos Cap", "Pikachu Alola Cap", "Pikachu Partner Cap"
    ]
}


# Define fusionable Pokémon
FUSION_POKEMON = ["mew", "chandelure", "mewtwo", "deoxys", "audino", "mawile"]

class PokemonInventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_pokemon(self, user_id, filters):
        conditions = ["userid = $1"]
        values = [user_id]
        idx = 2

        if filters["shiny"]:
            conditions.append("shiny = TRUE")

        if filters["fusion"]:
            conditions.append("fusionable = TRUE")

        if filters["favorite"]:
            conditions.append("favorite = TRUE")

        if filters["name"]:
            conditions.append("LOWER(pokemon_name) LIKE $" + str(idx))
            values.append(f"%{filters['name']}%")
            idx += 1

        # IV filter
        if filters["iv"]:
            op, value = filters["iv"]
            conditions.append(f"total_iv_percent {op} ${idx}")
            values.append(value)
            idx += 1

        # Stats filter
        stat_map = {
            "hp": "hp_iv", "attack": "attack_iv", "defense": "defense_iv",
            "spatk": "spatk_iv", "spdef": "spdef_iv", "speed": "speed_iv"
        }
        for stat, (op, value) in filters["stats"].items():
            if stat in stat_map:
                conditions.append(f"{stat_map[stat]} {op} ${idx}")
                values.append(value)
                idx += 1

        # Rarity filter
        if filters["legendary"]:
            conditions.append(f"pokemon_name = ANY(${idx})")
            values.append(RARE_POKEMON["legendary"])
            idx += 1
        elif filters["mythical"]:
            conditions.append(f"pokemon_name = ANY(${idx})")
            values.append(RARE_POKEMON["mythical"])
            idx += 1
        elif filters["ultrabeast"]:
            conditions.append(f"pokemon_name = ANY(${idx})")
            values.append(RARE_POKEMON["ultrabeast"])
            idx += 1
        elif filters["event"]:
            conditions.append(f"pokemon_name = ANY(${idx})")
            values.append(EVENT_POKEMON["event"])
            idx += 1
        elif filters["rare"]:
            all_rare = RARE_POKEMON["legendary"] + RARE_POKEMON["mythical"] + RARE_POKEMON["ultrabeast"]
            conditions.append(f"pokemon_name = ANY(${idx})")
            values.append(all_rare)
            idx += 1

        condition_str = " AND ".join(conditions)
        query = f"""
        SELECT pokemon_id, pokemon_name, level, total_iv_percent, shiny, favorite, fusionable,
               hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv, nickname
        FROM users_pokemon
        WHERE {condition_str}
        ORDER BY pokemon_id
        """

        async with self.bot.db.pool.acquire() as conn:
            return await conn.fetch(query, *values)

    @commands.command(name="pokemon", aliases=["p"])
    @is_not_suspended()
    async def pokemon_command(self, ctx, *args):
        user_id = ctx.author.id
        bot = ctx.bot

        stat_mapping = {
            "atk": "attack", "def": "defense", "spatk": "spatk",
            "spdef": "spdef", "hp": "hp", "spd": "speed"
        }

        filters = {
            "shiny": False, "name": None, "iv": None, "stats": {},
            "limit": None, "skip": None, "legendary": False,
            "mythical": False, "ultrabeast": False, "rare": False,
            "fusion": False, "favorite": False, "event": False
        }

        args = list(args)
        while args:
            arg = args.pop(0).lower()
            if arg in ["--shiny", "--sh"]:
                filters["shiny"] = True
            elif arg in ["--name", "--n"] and args:
                filters["name"] = args.pop(0).lower()
            elif arg in ["--limit", "--lim"] and args:
                filters["limit"] = int(args.pop(0))
            elif arg in ["--skip", "--sk"] and args:
                filters["skip"] = int(args.pop(0))
            elif arg in ["--rare", "--ra"]:
                filters["rare"] = True
            elif arg in ["--leg", "--legendary"]:
                filters["legendary"] = True
            elif arg in ["--ev", "--event"]:
                filters["event"] = True
            elif arg in ["--my", "--mythical"]:
                filters["mythical"] = True
            elif arg in ["--ub", "--ultrabeast"]:
                filters["ultrabeast"] = True
            elif arg in ["--fn", "--fusionable"]:
                filters["fusion"] = True
            elif arg in ["--fav", "--favorite"]:
                filters["favorite"] = True
            elif arg == "--iv" and args:
                iv_match = re.match(r'([<>]=?|=)?(\d+)', args[0])
                if iv_match:
                    op, value = iv_match.groups()
                    filters["iv"] = (op or "=", int(value))
                    args.pop(0)
            elif arg.startswith("--") and args:
                stat = stat_mapping.get(arg[2:], arg[2:])
                if stat in stat_mapping.values():
                    stat_match = re.match(r'([<>]=?|=)?(\d+)', args[0])
                    if stat_match:
                        op, value = stat_match.groups()
                        filters["stats"][stat] = (op or "=", int(value))
                        args.pop(0)

        try:
            inventory = await self.get_user_pokemon(user_id, filters)
            if not inventory:
                return await ctx.send("You don't have any Pokémon matching the filters!")
        except Exception as e:
            print(f"Error retrieving filtered inventory: {e}")
            return await ctx.send("An error occurred while retrieving your inventory.")

        def passes_filters(pokemon):
            if filters["shiny"] and not filter_shiny(pokemon, filters):
                return False
            if filters["name"] and not filter_name(pokemon, filters):
                return False
            if filters["iv"] and not filter_total_iv(pokemon, filters):
                return False
            if filters["fusion"] and not pokemon.get("fusionable", False):  # Check fusionable
                return False
            if filters["favorite"] and not pokemon.get("favorite", False):
                return False
            if not filter_stats(pokemon, filters):
                return False
            if not filter_rarity(pokemon, filters):
                return False
            return True

        filtered_inventory = [p for p in inventory if passes_filters(p)]
        filtered_inventory = filter_skip(filtered_inventory, filters, user_id, bot)
        filtered_inventory = filter_limit(filtered_inventory, filters, user_id, bot)

        total_pokemon = len(filtered_inventory)
        per_page = 20
        total_pages = max(1, ceil(total_pokemon / per_page))

        async def create_page_embed(page):
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            embed = discord.Embed(
                title=f"{ctx.author.display_name}'s Pokémon Inventory",
                color=discord.Color.green()
            )

            # Sort the filtered inventory by Pokémon ID
            order_cog = self.bot.get_cog("OrderCommands")  # Access the OrderCommands cog
            current_order = order_cog.order.get(user_id)  # Get current order for the user
            sorted_inventory = order_cog.sort_inventory(filtered_inventory, current_order)  # Sort the inventory

            description = []
            for pokemon in sorted_inventory[start_idx:end_idx]:
                pokemon_id = pokemon["pokemon_id"]
                name = pokemon["pokemon_name"]
                nickname = pokemon["nickname"]
                is_fusionable = pokemon["fusionable"]
                display_name = f"🧬 {name}" if is_fusionable else name
                is_favorite = pokemon["favorite"]
                if is_favorite:
                    display_name += " 💖"  # Add heart emoji if favorite
                is_shiny = pokemon["shiny"]
                level = pokemon["level"]
                iv = pokemon["total_iv_percent"]

                sprites_cog = self.bot.get_cog("Sprites")
                pokemon_emoji = await sprites_cog.get_pokemon_emoji(name)

                final_name = f"**{display_name}**"
                if nickname:
                    final_name += f' **"{nickname}"**'
                if is_shiny:
                    final_name = f"✨{final_name}"
                if pokemon_emoji != name:
                    final_name = f"{pokemon_emoji}  {final_name}"

                description.append(f"`{pokemon_id}`\u2002\u2002\u2002{final_name}\u2001•\u2001Lvl {level}\u2001•\u2001IV: {iv}%")

            embed.description = "\n".join(description) if description else "No Pokémon match your filters."
            embed.set_footer(
                text=f"Showing Pokémon {start_idx + 1}-{min(end_idx, total_pokemon)} out of {total_pokemon} | Page {page}/{total_pages}"
            )
            return embed

        current_page = 1
        embed = await create_page_embed(current_page)
        view = PaginationView(ctx, total_pages, create_page_embed)
        await ctx.send(embed=embed, view=view)


class PaginationView(View):
    def __init__(self, ctx, total_pages, create_page_embed):
        super().__init__()
        self.ctx = ctx
        self.total_pages = total_pages
        self.create_page_embed = create_page_embed
        self.current_page = 1

        self.prev_button = Button(label="◀️", style=discord.ButtonStyle.gray, disabled=True)
        self.next_button = Button(label="▶️", style=discord.ButtonStyle.gray, disabled=(total_pages == 1))

        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't use these buttons!", ephemeral=True)
            return

        self.current_page -= 1
        self.prev_button.disabled = self.current_page == 1
        self.next_button.disabled = False

        embed = await self.create_page_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't use these buttons!", ephemeral=True)
            return

        self.current_page += 1
        self.prev_button.disabled = False
        self.next_button.disabled = self.current_page == self.total_pages

        embed = await self.create_page_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

async def setup(bot):
    await bot.add_cog(PokemonInventory(bot))
