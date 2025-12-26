import discord

async def create_starters_embed(bot):
    """Creates an embed showing all Gen 1 to Gen 9 starter Pokémon in an organized way."""
    embed = discord.Embed(
        title="Choose Your Starter Pokémon!",
        description="To Pick your Starter, Use `@Pokédia#2537 pick <starter_name> .",
        color=discord.Color.green()
    )

    starters_by_generation = {
        "Generation 1 (Kanto)": ["bulbasaur", "charmander", "squirtle"],
        "Generation 2 (Johto)": ["chikorita", "cyndaquil", "totodile"],
        "Generation 3 (Hoenn)": ["treecko", "torchic", "mudkip"],
        "Generation 4 (Sinnoh)": ["turtwig", "chimchar", "piplup"],
        "Generation 5 (Unova)": ["snivy", "tepig", "oshawott"],
        "Generation 6 (Kalos)": ["chespin", "fennekin", "froakie"],
        "Generation 7 (Alola)": ["rowlet", "litten", "popplio"],
        "Generation 8 (Galar)": ["grookey", "scorbunny", "sobble"],
        "Generation 9 (Paldea)": ["sprigatito", "fuecoco", "quaxly"]
    }

    sprites_cog = bot.get_cog("Sprites")  # Get the Sprites cog instance

    for gen, pokemon_list in starters_by_generation.items():
        formatted_pokemon = []
        for pokemon in pokemon_list:
            emoji = await sprites_cog.get_pokemon_emoji(pokemon) if sprites_cog else pokemon  # Await here
            formatted_pokemon.append(f"{emoji} {pokemon.capitalize()}")  # Format with emoji

        embed.add_field(name=gen, value=" • ".join(formatted_pokemon), inline=False)

    return embed
