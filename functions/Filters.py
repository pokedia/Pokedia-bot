import re
import os
import json
import asyncpg

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
        "Calyrex", "Koraidon", "Miraidon", "Ogerpon", "Mewtwo"
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
        "Boss Squirtle", "Cupcake Swirlix", "Balloons Spheal", "Gifts Vulpix", "Mr Jester", "Waiter Snorlax", "Chef Teddiursa", "Hotchocolate Lotad", "Pikachu Belle", "Pikachu Libre", "Pikachu PhD", "Pikachu Pop Star", "Pikachu Rock Star", "Pikachu Original Cap", "Pikachu Hoenn Cap", "Pikachu Sinnoh Cap", "Pikachu Unova Cap", "Pikachu Kalos Cap", "Pikachu Alola Cap", "Pikachu Partner Cap",
        "Reindeer Manectric", "Lights Amaura", "Arctic Snow Zorua", "Christmas Timburr", "Tapu Bael", "Aurora Celebi", "Snowball Pikachu"
    ]
}


# Load aliases from alias.json
def load_aliases():
    aliases_path = os.path.join("functions", "alias.json")
    with open(aliases_path, "r", encoding="utf-8") as f:
        return json.load(f)

ALIASES = load_aliases()

def normalize_name(name):
    return name.replace(" ", "-").lower()

def filter_shiny(pokemon, filters):
    if filters["shiny"]:
        return pokemon.get("shiny", False)
    return True

def filter_name(pokemon, filters):
    name_filter = filters.get("name", None)
    if not name_filter:
        return False

    # Normalize the Pokémon name by replacing hyphens with spaces
    pokemon_name = pokemon["pokemon_name"].replace("-", " ").lower()
    name_filter = name_filter.replace("-", " ").lower()

    # Direct match check
    if pokemon_name == name_filter:
        return True

    # Check if the Pokémon name is in the aliases list
    name_filter_parts = name_filter.split()
    for original_name, aliases in ALIASES.items():
        normalized_original_name = original_name.replace("-", " ").lower()
        normalized_aliases = [alias.replace("-", " ").lower() for alias in aliases]

        for alias in normalized_aliases + [normalized_original_name]:  # Include original name
            alias_parts = alias.split()
            if all(part in alias_parts for part in name_filter_parts):
                if pokemon_name == normalized_original_name:
                    return True

    return False


def filter_total_iv(pokemon, filters):
    if filters["iv"]:
        op, value = filters["iv"]
        pokemon_iv = pokemon.get("total_iv_percent", 0)
        if op == "=" and pokemon_iv != value:
            return False
        elif op == ">" and pokemon_iv <= value:
            return False
        elif op == "<" and pokemon_iv >= value:
            return False
        elif op == ">=" and pokemon_iv < value:
            return False
        elif op == "<=" and pokemon_iv > value:
            return False
    return True


def filter_stats(pokemon, filters):
      # Debugging line

    for stat, (op, value) in filters.get("stats", {}).items():
        stat_column = f"{stat}_iv"

        # Ensure we're accessing the stat correctly
        if stat_column in pokemon:
            pokemon_stat_iv = pokemon[stat_column]  # Direct access since it's an asyncpg.Record
        else:
              # Debugging line
            return False  # If stat is missing, it fails the filter

          # Debugging line

        # Apply filtering logic
        if op == "=" and pokemon_stat_iv != value:
            return False
        elif op == ">" and pokemon_stat_iv <= value:
            return False
        elif op == "<" and pokemon_stat_iv >= value:
            return False
        elif op == ">=" and pokemon_stat_iv < value:
            return False
        elif op == "<=" and pokemon_stat_iv > value:
            return False

    return True



def filter_rarity(pokemon, filters):
    pokemon_name = pokemon.get("pokemon_name", "")

    if filters.get("rare", False):
        return any(pokemon_name in RARE_POKEMON[category] for category in RARE_POKEMON)

    if filters.get("legendary", False) and pokemon_name not in RARE_POKEMON["legendary"]:
        return False
    if filters.get("mythical", False) and pokemon_name not in RARE_POKEMON["mythical"]:
        return False
    if filters.get("ultrabeast", False) and pokemon_name not in RARE_POKEMON["ultrabeast"]:
        return False
    if filters.get("event", False) or filters.get("ev", False):
        return pokemon_name in EVENT_POKEMON["event"]

    return True

def filter_limit(inventory, filters, user_id, bot):
    order_cog = bot.get_cog("OrderCommands")
    if order_cog:
        order = order_cog.order.get(user_id)
        inventory = order_cog.sort_inventory(inventory, order) if order else inventory

    if "limit" in filters and isinstance(filters["limit"], int):
        return inventory[:filters["limit"]]
    return inventory

def filter_skip(inventory, filters, user_id, bot):
    order_cog = bot.get_cog("OrderCommands")
    if order_cog:
        order = order_cog.order.get(user_id)
        inventory = order_cog.sort_inventory(inventory, order) if order else inventory

    if "skip" in filters and isinstance(filters["skip"], int):
        return inventory[filters["skip"]:]
    return inventory

async def filter_fusion(user_id, db_pool):
    query = """
    SELECT pokemon_name FROM users_pokemon
    WHERE userid = $1 AND fusionable = TRUE
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, user_id)
        return [row["pokemon_name"] for row in rows]

async def filter_favorite(user_id, db_pool):
    query = """
    SELECT pokemon_name FROM users_pokemon
    WHERE userid = $1 AND favorite = TRUE
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, user_id)
        return [row["pokemon_name"] for row in rows]