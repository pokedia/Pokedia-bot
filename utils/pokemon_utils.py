def is_valid_starter(pokemon_name):
    """Checks if the given Pokémon name is a valid starter (case-insensitive)."""
    starters = [
        "Bulbasaur", "Charmander", "Squirtle",
        "Chikorita", "Cyndaquil", "Totodile",
        "Treecko", "Torchic", "Mudkip",
        "Turtwig", "Chimchar", "Piplup",
        "Snivy", "Tepig", "Oshawott",
        "Chespin", "Fennekin", "Froakie",
        "Rowlet", "Litten", "Popplio",
        "Grookey", "Scorbunny", "Sobble",
        "Sprigatito", "Fuecoco", "Quaxly"
    ]
    return pokemon_name.lower() in [starter.lower() for starter in starters]


def generate_pokemon(pokemon_name):
    """Generates a Pokémon with Level 1 and a random IV percentage."""
    from random import randint
    return {
        "name": pokemon_name,
        "level": 1,
        "iv_percentage": randint(1, 100)  # Fixed: Added missing parenthesis
    }


import json

def get_base_stats(pokemon_name):
    """
    Fetches base stats for a given Pokémon from the base_stats.json file.
    Tries the name in four formats:
    1. Original case (with hyphens)
    2. All lowercase
    3. First letter capitalized
    4. Every word capitalized (handles names like 'Alolan-Vulpix')
    Returns a dictionary with stats or None if not found.
    """
    try:
        # Open and load the base stats JSON file
        with open("base_stats.json", "r") as file:
            base_stats = json.load(file)

        # 1. Try the original name
        if pokemon_name in base_stats:
            return base_stats[pokemon_name]

        # 2. Try all lowercase
        normalized_name_lower = pokemon_name.lower()
        if normalized_name_lower in base_stats:
            return base_stats[normalized_name_lower]

        # 3. Try with the first letter capitalized
        normalized_name_capitalized = pokemon_name.capitalize()
        if normalized_name_capitalized in base_stats:
            return base_stats[normalized_name_capitalized]

        # 4. Try capitalizing every word (handling hyphenated names)
        normalized_name_title = "-".join(word.capitalize() for word in pokemon_name.split("-"))
        if normalized_name_title in base_stats:
            return base_stats[normalized_name_title]

        # If no match is found, return None
        return None
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading base stats: {e}")
        return None



import random

import random  # Ensure random is imported

import random

import random

def generate_stats(base_stats, iv_percentage, level):
    """
    Generates Pokémon stats using the given IV percentage and level.

    1. Calculates total target IVs based on iv_percentage.
    2. Randomly distributes IVs across all stats to match the exact total.
    3. Calculates final stat values based on IVs and base stats.

    :param base_stats: Dict of base stats (keys: hp, attack, defense, special-attack, special-defense, speed).
    :param iv_percentage: Desired total IV percentage (0–100).
    :param level: Pokémon level (1–100).
    :return: Dict containing each stat's value and IV, and total IV percentage.
    """
    stat_keys = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
    stats = {}

    total_possible_iv = 31 * len(stat_keys)  # Max IVs = 186
    target_total_iv = round((iv_percentage / 100) * total_possible_iv)

    # Step 1: Generate IVs to exactly match target_total_iv
    ivs = [0] * len(stat_keys)
    for _ in range(target_total_iv):
        idx = random.randint(0, len(ivs) - 1)
        if ivs[idx] < 31:
            ivs[idx] += 1
        else:
            # If already maxed, retry a different index
            while True:
                idx = random.randint(0, len(ivs) - 1)
                if ivs[idx] < 31:
                    ivs[idx] += 1
                    break

    # Step 2: Calculate stats using formula
    for i, stat in enumerate(stat_keys):
        iv = ivs[i]
        base = base_stats[stat]
        if stat == "hp":
            value = ((2 * base + iv) * level) // 100 + level + 10
        else:
            value = ((2 * base + iv) * level) // 100 + 5
        stats[stat] = {"value": value, "iv": iv}

    # Step 3: Include total IV %
    final_total_iv = sum(ivs)
    stats["total_iv"] = round((final_total_iv / total_possible_iv) * 100, 2)

    return stats





import requests

def is_valid_pokemon(pokemon_name):
    try:
        # Fetch Pokémon data using PokeAPI or a similar service
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error fetching Pokémon: {e}")
        return False


import random

def is_shiny() -> bool:
    """Determines if a Pokémon is shiny with a 1 in 4096 chance."""
    shiny_chance = 4096
    roll = random.randint(1, shiny_chance)
    return roll == 1

import re

def parse_and_apply_filters(inventory, args):
    """
    Filters the Pokémon inventory based on provided arguments.

    Args:
        inventory (list): List of Pokémon dictionaries.
        args (list): List of filter arguments (e.g., --shiny, --level>10).

    Returns:
        list: Filtered inventory of Pokémon.
    """
    filters = {}
    comparator_pattern = re.compile(r"(>=|<=|>|<|=)(\d+)$")  # Matches comparison operators and numbers

    for arg in args:
        if arg.startswith("--shiny"):
            filters["shiny"] = True
        elif arg.startswith("--name="):
            filters["name"] = arg.split("=")[1].lower()
        elif arg.startswith("--level"):
            match = comparator_pattern.search(arg)
            if match:
                filters["level"] = (match.group(1), int(match.group(2)))
        elif arg.startswith("--iv"):
            match = comparator_pattern.search(arg)
            if match:
                filters["iv"] = (match.group(1), int(match.group(2)))
        elif arg.startswith("--") and "iv" in arg:
            stat = arg[2:-2]  # Extracts the stat (e.g., "atk" from "--atkiv")
            match = comparator_pattern.search(arg)
            if match:
                filters[f"{stat}_iv"] = (match.group(1), int(match.group(2)))

    def matches_filters(pokemon):
        # Filter for shiny Pokémon
        if filters.get("shiny") and not pokemon.get("is_shiny", False):
            return False

        # Filter for name
        if "name" in filters and filters["name"] not in pokemon.get("name", "").lower():
            return False

        # Filter for level
        if "level" in filters:
            operator, value = filters["level"]
            if not eval(f"pokemon['level'] {operator} {value}"):
                return False

        # Filter for overall IV
        if "iv" in filters:
            operator, value = filters["iv"]
            if not eval(f"pokemon['iv'] {operator} {value}"):
                return False

        # Filter for specific stat IVs (atk_iv, def_iv, etc.)
        for stat_key, (operator, value) in filters.items():
            if stat_key.endswith("_iv") and not eval(f"pokemon.get('{stat_key}', 0) {operator} {value}"):
                return False

        return True

    # Apply filters to the inventory
    filtered_inventory = [pokemon for pokemon in inventory if matches_filters(pokemon)]

    return filtered_inventory


