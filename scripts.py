import os
import json

BASE_DIR = r"C:\Users\vedan\images\final"  # your final folder
OUTPUT_FILE = "number.json"

data = {}

for pokemon in os.listdir(BASE_DIR):
    pokemon_path = os.path.join(BASE_DIR, pokemon)

    if not os.path.isdir(pokemon_path):
        continue

    png_count = sum(
        1 for f in os.listdir(pokemon_path)
        if f.lower().endswith(".png")
    )

    if png_count > 0:
        data[pokemon.lower()] = png_count

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print(f"✅ number.json generated with {len(data)} Pokémon")

