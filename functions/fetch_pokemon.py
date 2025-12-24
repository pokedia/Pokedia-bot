import json
import random


def fetch_pokemon_name():
    try:
        # Open the correct JSON file (spawn_rarity.json)
        with open("spawn_rarity.json", "r") as f:
            rarity_data = json.load(f)

        # Create lists for Pokémon names and their respective spawn chances (weights)
        pokemon_names = []
        weights = []

        # Add each Pokémon name and its corresponding weight (spawn rate) to the lists
        for entry in rarity_data:
            pokemon_name = entry["pokemon"]
            spawn_chance = entry["chance"]

            # Handle the "1/x" chance format by converting it to an integer value
            spawn_rate = int(spawn_chance.split("/")[1])  # Only use the denominator as the spawn rate

            # Invert the spawn rate to give higher spawn rates (lower denominators) higher weights
            weight = 1000 // spawn_rate  # Invert the denominator to adjust the weight

            # Add the Pokémon name and its weight to the lists
            pokemon_names.append(pokemon_name)
            weights.append(weight)

        # Use random.choices() to select a Pokémon based on the weighted spawn chances
        if pokemon_names:
            selected_pokemon = random.choices(pokemon_names, weights=weights, k=1)[0]
            return selected_pokemon
        else:
            return None

    except FileNotFoundError:
        print("Error: spawn_rarity.json file not found!")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in spawn_rarity.json!")
        return None
