import discord
from discord.ext import commands
from discord.ui import View, Button
from pymongo.common import aliases
from utils.susp_check import is_not_suspended

from functions.Filters import filter_name, filter_shiny, filter_total_iv, filter_stats, filter_rarity, filter_skip, \
    filter_limit
import re


class ConfirmView(View):
    def __init__(self, user_id, bot, ctx, filtered_pokemon):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.bot = bot
        self.ctx = ctx
        self.filtered_pokemon = filtered_pokemon

    async def favorite_all(self):
        async with self.bot.db.pool.acquire() as conn:
            query = """
            UPDATE users_pokemon
            SET favorite = TRUE
            WHERE userid = $1 AND pokemon_id = ANY($2)
            """
            pokemon_ids = [p["pokemon_id"] for p in self.filtered_pokemon]
            await conn.execute(query, self.user_id, pokemon_ids)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This is not your confirmation request!", ephemeral=True)

        await self.favorite_all()
        await interaction.response.edit_message(content="All selected Pokémon have been favorited!", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This is not your confirmation request!", ephemeral=True)

        await interaction.response.edit_message(content="Action canceled.", view=None)


class Favorite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="favorite", aliases=["fav"])
    @is_not_suspended()
    async def fav(self, ctx, pokemon_id: int):
        """Marks a Pokémon as favorite by its ID."""
        user_id = ctx.author.id

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot favorite a pokemon while in trade.")
            return

        async with self.bot.db.pool.acquire() as conn:
            query = """
            SELECT unique_id FROM users_pokemon
            WHERE userid = $1 AND pokemon_id = $2
            """
            result = await conn.fetchrow(query, user_id, pokemon_id)

            if not result:
                return await ctx.send("You do not own a Pokémon with this ID.")

            update_query = """
            UPDATE users_pokemon
            SET favorite = TRUE
            WHERE userid = $1 AND pokemon_id = $2
            """
            await conn.execute(update_query, user_id, pokemon_id)
            await ctx.send(f"Pokémon with ID {pokemon_id} has been marked as favorite!")

    @commands.command(aliases=["fa", "favoriteall"])
    @is_not_suspended()
    async def favorite_all(self, ctx, *, args: str):
        """Favorites all Pokémon that match the given filters."""
        user_id = ctx.author.id

        trade_cog = self.bot.get_cog("Trade")
        if trade_cog and trade_cog.trade_system.active_trade(ctx.author):  # No 'await' here
            await ctx.send("You cannot favorite a pokemon while in trade.")
            return

        async with self.bot.db.pool.acquire() as conn:
            query = """
            SELECT * FROM users_pokemon WHERE userid = $1
            """
            all_pokemon = await conn.fetch(query, user_id)

        stat_mapping = {
            "atk": "attack", "def": "defense", "spatk": "spatk",
            "spdef": "spdef", "hp": "hp", "spd": "speed"
        }

        filters = {
            "shiny": False, "name": None, "iv": None, "stats": {},
            "limit": None, "skip": None, "legendary": False,
            "mythical": False, "ultrabeast": False, "rare": False,
            "fusion": False, "favorite": False
        }

        args = args.split()
        parsed_args = {}

        while args:
            arg = args.pop(0).lower()
            if arg in ["--shiny", "--sh"]:
                parsed_args["shiny"] = True
            elif arg in ["--name", "--n"] and args:
                parsed_args["name"] = args.pop(0).lower()
            elif arg == "--limit" and args:
                parsed_args["limit"] = int(args.pop(0))
            elif arg == "--skip" and args:
                parsed_args["skip"] = int(args.pop(0))
            elif arg in ["--rare"]:
                parsed_args["rare"] = True
            elif arg in ["--leg", "--legendary"]:
                parsed_args["legendary"] = True
            elif arg in ["--my", "--mythical"]:
                parsed_args["mythical"] = True
            elif arg in ["--ub", "--ultrabeast"]:
                parsed_args["ultrabeast"] = True
            elif arg in ["--fn", "--fusionable"]:
                parsed_args["fusion"] = True
            elif arg in ["--fav", "--favorite"]:
                parsed_args["favorite"] = True
            elif arg == "--iv" and args:
                iv_match = re.match(r'([<>]=?|=)?(\d+)', args[0])
                if iv_match:
                    op, value = iv_match.groups()
                    parsed_args["iv"] = (op or "=", int(value))
                    args.pop(0)
            elif arg.startswith("--") and args:
                stat = stat_mapping.get(arg[2:], arg[2:])
                if stat in stat_mapping.values():
                    stat_match = re.match(r'([<>]=?|=)?(\d+)', args[0])
                    if stat_match:
                        op, value = stat_match.groups()
                        parsed_args.setdefault("stats", {})[stat] = (op or "=", int(value))
                        args.pop(0)

        filters.update(parsed_args)

        def passes_filters(pokemon):
            if filters["shiny"] and not filter_shiny(pokemon, filters):
                return False
            if filters["name"] and not filter_name(pokemon, filters):
                return False
            if filters["iv"] and not filter_total_iv(pokemon, filters):
                return False
            if filters["fusion"] and not pokemon.get("fusionable", False):
                return False
            if filters["favorite"] and not pokemon.get("favorite", False):
                return False
            if not filter_stats(pokemon, filters):
                return False
            if not filter_rarity(pokemon, filters):
                return False
            return True

        filtered_inventory = [p for p in all_pokemon if passes_filters(p)]
        filtered_inventory = filter_skip(filtered_inventory, filters, user_id, self.bot)
        filtered_inventory = filter_limit(filtered_inventory, filters, user_id, self.bot)

        if not filtered_inventory:
            return await ctx.send("No Pokémon match your filters.")

        view = ConfirmView(user_id, self.bot, ctx, filtered_inventory)
        await ctx.send(f"Are you sure you want to favorite {len(filtered_inventory)} Pokémon?", view=view)


async def setup(bot):
    await bot.add_cog(Favorite(bot))

