import discord
from discord.ext import commands
import random
from utils.susp_check import is_not_suspended


class PokemonHint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.previous_hints = {}

    @commands.command()
    @is_not_suspended()
    async def hint(self, ctx):
        channel_id = str(ctx.channel.id)

        if channel_id not in self.bot.channel_spawns or not self.bot.channel_spawns[channel_id]:
            await ctx.send("No Pokémon to guess in this channel!")
            return

        pokemon_data = self.bot.channel_spawns[channel_id]
        if isinstance(pokemon_data, dict) and 'name' in pokemon_data:
            pokemon_name = pokemon_data['name'].lower()
        else:
            await ctx.send("Invalid Pokémon data.")
            return

        # Generate a new hint pattern
        hint_pattern = self.generate_hint(channel_id, pokemon_name)
        self.previous_hints[channel_id] = hint_pattern

        await ctx.send(f"Here's your hint: `{hint_pattern}`")

    def generate_hint(self, channel_id, pokemon_name):
        # If it's a new Pokémon OR previous hint is not a dict, reset
        if (
                channel_id not in self.previous_hints or
                not isinstance(self.previous_hints[channel_id], dict) or
                self.previous_hints[channel_id].get("name") != pokemon_name
        ):
            self.previous_hints[channel_id] = {
                "name": pokemon_name,
                "hint": ['_'] * len(pokemon_name)
            }

        hint = self.previous_hints[channel_id]["hint"]
        num_to_reveal = max(1, len(pokemon_name) // 3)

        # Find positions still hidden
        available_indices = [i for i, c in enumerate(hint) if c == '_']
        if len(available_indices) < num_to_reveal:
            num_to_reveal = len(available_indices)

        # Reveal some hidden letters
        reveal_indices = random.sample(available_indices, num_to_reveal)
        for i in reveal_indices:
            hint[i] = pokemon_name[i]

        return ' '.join(hint)

async def setup(bot):
    await bot.add_cog(PokemonHint(bot))
