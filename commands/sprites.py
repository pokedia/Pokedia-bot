import discord
from discord.ext import commands

class Sprites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pokemon_sprites = {
            "bulbasaur": "1335511525674188841",
            "charmander": "1335518741815099403",
            "squirtle": "1335519110737428536",
            "chikorita": "1335518800539291720",
            "cyndaquil": "1335519147810881546",
            "totodile": "1335519205965168782",
            "froakie": "1335879054242480148",
            "ironthorns": "1335903095401615421",
            "mew": "1336332216678219836",
            "mewlander": "1336361759589793792",
            "mewoxys": "1336381657128632320",
            "abomasnow": "1337017065114177556",
            "aggron": "1337018524346093619",
            "waitersnorlax": "1367199613185949777",
            "mrjester": "1367199655917781125"
        }

    async def get_pokemon_emoji(self, name: str) -> str:
        """Returns the formatted emoji for a given Pokémon name."""
        name = name.lower().replace(" ", "")  # Remove hyphens from the name
        emoji_id = self.pokemon_sprites.get(name)
        return f"<:{name}:{emoji_id}>" if emoji_id else name  # Fallback to name if no emoji is found

async def setup(bot):
    await bot.add_cog(Sprites(bot))
