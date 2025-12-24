import discord
from discord.ext import commands
import asyncio
from database import Database
from functions.trade_filters import filter_shiny, filter_name, filter_total_iv, filter_stats, filter_rarity, filter_limit, filter_skip, filter_fusion

class TradeSystem:
    def __init__(self, db):# ✅ Store the bot instance
        self.db = db                  # ✅ Database connection
        self.trades = {}
        self.active_trades = {}
        self.active_requests = set()


    def active_trade(self, user):
        # Check if the user is in any active trade
        return any(user.id in trade for trade in self.active_trades.keys())


    async def send_trade_embed(self, channel, user1, user2, trade_data, confirmations, page=1):
        items_per_page = 20
        total_items = max(len(trade_data[user1.id]), len(trade_data[user2.id]))
        total_pages = max(1, (total_items // items_per_page) + (1 if total_items % items_per_page else 0))

        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        # Format trade data to ensure numbers have commas
        def format_entry(entry):
            parts = entry.split()
            if len(parts) == 2 and parts[1].lower() == "cash":  # If entry is like "1000 cash"
                try:
                    return f"{int(parts[0]):,} {parts[1]}"  # Format number with commas
                except ValueError:
                    return entry  # If conversion fails, return as is
            return entry

        formatted_user1_items = [format_entry(entry) for entry in trade_data[user1.id][start_idx:end_idx]]
        formatted_user2_items = [format_entry(entry) for entry in trade_data[user2.id][start_idx:end_idx]]

        embed = discord.Embed(title=f"Trade between {user1.name} & {user2.name}", color=discord.Color.blue())
        embed.add_field(
            name=("✅ " if confirmations[user1.id] else "") + user1.name,
            value="\n".join(formatted_user1_items) or "None", inline=True
        )
        embed.add_field(
            name=("✅ " if confirmations[user2.id] else "") + user2.name,
            value="\n".join(formatted_user2_items) or "None", inline=True
        )
        embed.set_footer(
            text=f"Showing Page {page}/{total_pages}\nNote: Trade at your own risk, it is suggested to always check prices before trading for safety."
        )

        msg = await channel.send(embed=embed)
        if total_pages > 1:
            await msg.add_reaction("⬅️")
            await msg.add_reaction("➡️")
        return msg

    async def handle_pagination(self, reaction, user):
        for trade_key, trade in self.active_trades.items():
            if trade.get("embed_msg") and trade["embed_msg"].id == reaction.message.id:
                if user.id not in trade:
                    return

                total_items = max(len(trade[trade_key[0]]), len(trade[trade_key[1]]))
                total_pages = max(1, (total_items // 20) + (1 if total_items % 20 else 0))

                if reaction.emoji == "⬅️" and trade["page"] > 1:
                    trade["page"] -= 1
                elif reaction.emoji == "➡️" and trade["page"] < total_pages:
                    trade["page"] += 1
                else:
                    return

                user1 = await reaction.message.guild.fetch_member(trade_key[0])
                user2 = await reaction.message.guild.fetch_member(trade_key[1])
                await trade["embed_msg"].edit(embed=(await self.send_trade_embed(reaction.message.channel, user1, user2, trade, trade["confirmed"], trade["page"])).embed)
                break

    async def start_trade(self, ctx, user1, user2):
        if user1 == user2:
            await ctx.send("You cannot trade with yourself!")
            return

        if user1.id in self.active_requests or user2.id in self.active_requests:
            await ctx.send("One of you already has a pending trade request! Please wait for it to be accepted or declined.")
            return

        if self.active_trade(user1) or self.active_trade(user2):
            await ctx.send("One of you is already in an active trade! Finish your current trade first.")
            return

        if user2.bot or user1.bot:
            await ctx.send("You cannot trade with a bot!")
            return

        trade_key = (user1.id, user2.id)
        self.active_requests.add(user1.id)
        self.active_requests.add(user2.id)

        message = await ctx.send(
            f"{user2.mention}, {user1.mention} wants to trade! React with ✅ to accept or ❌ to decline."
        )
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction, user):
            return user == user2 and str(reaction.emoji) in ["✅", "❌"]

        try:
            reaction, _ = await ctx.bot.wait_for("reaction_add", check=check, timeout=60)
        except asyncio.TimeoutError:
            await message.edit(content="Trade request timed out.")
            self.active_requests.discard(user1.id)
            self.active_requests.discard(user2.id)
            return

        self.active_requests.discard(user1.id)
        self.active_requests.discard(user2.id)

        if str(reaction.emoji) == "✅":
            self.active_trades[trade_key] = {
                user1.id: [], user2.id: [],
                "confirmed": {user1.id: False, user2.id: False},
                "page": 1,
                "accepted": True  # ✅ Trade is now marked as accepted!
            }

            await message.edit(content=f"Trade accepted! {user1.mention} and {user2.mention}, add items using `!ta <item>`.")

            trade_embed = await self.send_trade_embed(ctx.channel, user1, user2, self.active_trades[trade_key],
                                                      self.active_trades[trade_key]["confirmed"])
            self.active_trades[trade_key]["embed_msg"] = trade_embed
        else:
            await message.edit(content=f"Trade declined by {user2.mention}.")

    async def add_trade_item(self, ctx, user, item):
        trade_key = next((k for k in self.active_trades if user.id in k), None)
        if not trade_key:
            await ctx.send("You are not in an active trade!")
            return

        if self.active_trades[trade_key]["confirmed"][user.id]:
            self.active_trades[trade_key]["confirmed"][user.id] = False
            await ctx.send(f"Confirmation has been reversed for {user.name} because they added a new item.")

        self.active_trades[trade_key]["confirmed"] = {trade_key[0]: False, trade_key[1]: False}

        items = item.split()
        item_descs = []

        # Extract existing items in trade
        existing_entries = self.active_trades[trade_key][user.id]

        user_data = await self.db.fetchrow("SELECT pokecash, redeems FROM users WHERE userid = $1", user.id)
        if not user_data:
            await ctx.send("User data not found.")
            return

        user_cash = user_data["pokecash"]
        user_redeems = user_data["redeems"]

        # Check if the command is for cash or redeem
        if len(items) == 2:
            if items[0].lower() == "cash" and items[1].isdigit():
                amount = int(items[1])
                if amount <= 0:
                    await ctx.send("Cash amount must be positive.")
                    return

                current_trade_cash = sum(int(entry.split()[0]) for entry in existing_entries if "cash" in entry)
                if (current_trade_cash + amount) > user_cash:
                    await ctx.send("You don't have enough cash to add to the trade.")
                    return

                # Update existing cash entry instead of adding duplicate
                for i, entry in enumerate(existing_entries):
                    if "cash" in entry:
                        existing_amount = int(entry.split()[0])
                        new_amount = existing_amount + amount
                        existing_entries[i] = f"{new_amount} cash"
                        break
                else:
                    item_descs.append(f"{amount} cash")

            elif items[0].lower() == "redeem" and items[1].isdigit():
                amount = int(items[1])
                if amount <= 0:
                    await ctx.send("Redeem amount must be positive.")
                    return

                current_trade_redeems = sum(int(entry.split()[0]) for entry in existing_entries if "redeem" in entry)
                if (current_trade_redeems + amount) > user_redeems:
                    await ctx.send("You don't have enough redeems to add to the trade.")
                    return

                # Update existing redeem entry instead of adding duplicate
                for i, entry in enumerate(existing_entries):
                    if "redeem" in entry:
                        existing_amount = int(entry.split()[0])
                        new_amount = existing_amount + amount
                        existing_entries[i] = f"{new_amount} redeem(s)"
                        break
                else:
                    item_descs.append(f"{amount} redeem(s)")

            else:
                await ctx.send("Please use the command as either `!ta cash <amount>` or `!ta redeem <amount>`.")
                return


        else:

            # Handle Pokémon ID entries (multiple allowed)

            existing_pokemon_ids = {

                int(entry.split(" • ")[0]) for entry in existing_entries if " • " in entry

            }

            processed_ids = set()  # Track IDs in this command only

            for id in items:

                if not id.isdigit():
                    await ctx.send(f"Invalid ID `{id}`. Use numbers or `!ta cash <amount>` / `!ta redeem <amount>`.")
                    continue

                pokemon_id = int(id)
                if pokemon_id in processed_ids:
                    continue  # Already processed in this command
                processed_ids.add(pokemon_id)
                if pokemon_id in existing_pokemon_ids:
                    await ctx.send(f"Pokémon ID `{pokemon_id}` is already in the trade!")
                    continue

                pokemon = await self.db.get_pokemon(user.id, pokemon_id)
                if not pokemon:
                    await ctx.send(f"Pokémon ID `{pokemon_id}` not found!")
                    continue

                if pokemon.get("selected") or pokemon.get("favorite"):
                    await ctx.send(f"Pokémon ID `{pokemon_id}` is marked as selected or favorite and cannot be traded!")
                    continue

                shiny_symbol = "✨ " if pokemon.get("shiny") else ""
                fusion_symbol = "🧬 " if pokemon.get("fusionable") else ""
                item_desc = f"{pokemon_id} • {fusion_symbol}{shiny_symbol}{pokemon['pokemon_name']} • Lvl {pokemon['level']} • {pokemon['total_iv_percent']:.2f}%"
                item_descs.append(item_desc)

        # Add unique item descriptions to the trade
        self.active_trades[trade_key][user.id].extend(item_descs)
        print(f"Trade items for {user.name}: {self.active_trades[trade_key][user.id]}")

        user1 = await ctx.guild.fetch_member(trade_key[0])
        user2 = await ctx.guild.fetch_member(trade_key[1])

        old_embed_msg = self.active_trades[trade_key].get("embed_msg")
        if old_embed_msg:
            await old_embed_msg.delete()

        new_embed_msg = await self.send_trade_embed(ctx.channel, user1, user2, self.active_trades[trade_key],
                                                    self.active_trades[trade_key]["confirmed"])
        self.active_trades[trade_key]["embed_msg"] = new_embed_msg
        print("New trade embed sent.")

    async def confirm_trade(self, ctx, user):
        trade_key = next((k for k in self.active_trades if user.id in k), None)
        if not trade_key:
            await ctx.send("You are not in an active trade!")
            return

        self.active_trades[trade_key]["confirmed"][user.id] = True

        user1 = await ctx.guild.fetch_member(trade_key[0])
        user2 = await ctx.guild.fetch_member(trade_key[1])

        # Delete old embed message
        old_embed_msg = self.active_trades[trade_key].get("embed_msg")
        if old_embed_msg:
            await old_embed_msg.delete()

        # Send updated embed with confirmation status
        new_embed_msg = await self.send_trade_embed(
            ctx.channel, user1, user2, self.active_trades[trade_key],
            self.active_trades[trade_key]["confirmed"]
        )
        self.active_trades[trade_key]["embed_msg"] = new_embed_msg

        # Check if both users confirmed
        if all(self.active_trades[trade_key]["confirmed"].values()):
            await ctx.send(f"Trade between {user1.mention} and {user2.mention} completed!")
            await self.finalize_trade(user1.id, user2.id, self.active_trades[trade_key])
            del self.active_trades[trade_key]

    async def finalize_trade(self, user1_id, user2_id, trade_data):
        # Finalize the trade for user1
        for item in trade_data[user1_id]:
            if "cash" in item:
                amount = int(item.split()[0])
                await self.db.transfer_cash(user1_id, user2_id, amount)
            elif "redeem" in item:
                amount = int(item.split()[0])
                try:
                    await self.db.transfer_redeems(user1_id, user2_id, amount)
                except ValueError as e:
                    print(f"Error transferring redeems: {e}")
                    return
            else:
                pokemon_id = int(item.split(" • ")[0])
                # Transfer the Pokémon to user2
                success = await self.db.transfer_pokemon(user1_id, user2_id, pokemon_id)
                if not success:
                    print(f"Failed to transfer Pokémon ID {pokemon_id} from {user1_id} to {user2_id}")

        # Finalize the trade for user2
        for item in trade_data[user2_id]:
            if "cash" in item:
                amount = int(item.split()[0])
                await self.db.transfer_cash(user2_id, user1_id, amount)
            elif "redeem" in item:
                amount = int(item.split()[0])
                try:
                    await self.db.transfer_redeems(user2_id, user1_id, amount)
                except ValueError as e:
                    print(f"Error transferring redeems: {e}")
                    return
            else:
                pokemon_id = int(item.split(" • ")[0])
                # Transfer the Pokémon to user1
                success = await self.db.transfer_pokemon(user2_id, user1_id, pokemon_id)
                if not success:
                    print(f"Failed to transfer Pokémon ID {pokemon_id} from {user2_id} to {user1_id}")

    async def cancel_trade(self, ctx, user):
        trade_key = next((k for k in self.active_trades if user.id in k), None)
        if not trade_key:
            await ctx.send("You are not in an active trade!")
            return

        user1 = await ctx.guild.fetch_member(trade_key[0])
        user2 = await ctx.guild.fetch_member(trade_key[1])

        del self.active_trades[trade_key]
        await ctx.send(f"Trade between {user1.mention} and {user2.mention} has been canceled.")

    async def remove_trade_item(self, ctx, user, item):
        trade_key = next((k for k in self.active_trades if user.id in k), None)
        if not trade_key:
            await ctx.send("You are not in an active trade!")
            return

        trade_data = self.active_trades[trade_key]
        user_items = trade_data[user.id]

        item = item.strip().lower()
        removed = False

        # Reset the user's confirmation
        if trade_data["confirmed"][user.id]:
            trade_data["confirmed"][user.id] = False
            await ctx.send(f"Confirmation has been reversed for {user.name} because they removed an item.")

        # Case 1: Removing cash
        if item.startswith("cash"):
            amount = item.replace("cash", "").strip()
            if amount.isdigit():
                amount = int(amount)
                for i, entry in enumerate(user_items):
                    if "cash" in entry:
                        existing_amount = int(entry.split()[0])
                        if amount == existing_amount:
                            user_items.pop(i)  # Remove the exact amount
                            removed = True
                            break
                        elif amount < existing_amount:
                            user_items[i] = f"{existing_amount - amount} cash"  # Reduce the amount
                            removed = True
                            break

        # Case 2: Removing redeem
        elif item.startswith("redeem"):
            amount = item.replace("redeem", "").replace("(s)", "").strip()
            if amount.isdigit():
                amount = int(amount)
                for i, entry in enumerate(user_items):
                    if "redeem" in entry:
                        existing_amount = int(entry.split()[0])
                        if amount == existing_amount:
                            user_items.pop(i)  # Remove the exact amount
                            removed = True
                            break
                        elif amount < existing_amount:
                            user_items[i] = f"{existing_amount - amount} redeem(s)"  # Reduce the amount
                            removed = True
                            break

        # Case 3: Removing Pokémon by ID
        elif item.isdigit():
            pokemon_id = int(item)
            for i, entry in enumerate(user_items):
                if entry.startswith(f"{pokemon_id} •"):
                    user_items.pop(i)  # Remove the Pokémon
                    removed = True
                    break

        if not removed:
            await ctx.send("Couldn't find the specified item or the exact amount on your side of the trade.")
            return

        # Refresh the trade embed
        user1 = await ctx.guild.fetch_member(trade_key[0])
        user2 = await ctx.guild.fetch_member(trade_key[1])

        old_embed_msg = trade_data.get("embed_msg")
        if old_embed_msg:
            await old_embed_msg.delete()

        new_embed_msg = await self.send_trade_embed(ctx.channel, user1, user2, trade_data, trade_data["confirmed"])
        trade_data["embed_msg"] = new_embed_msg

        await ctx.send(f"{item} removed from the trade.")
        print(f"Item removed from {user.name}'s trade items.")

    async def trade_add_all(self, ctx, user, filters):
        trade_data = self.active_trades.get(user.id, {})
        user_id = ctx.author.id
        bot = ctx.bot
        trade_key = next((k for k in self.active_trades if user.id in k), None)

        if not trade_key:
            await ctx.send("You are not in an active trade!")
            return

        if self.active_trades[trade_key]["confirmed"][user.id]:
            self.active_trades[trade_key]["confirmed"][user.id] = False
            await ctx.send(f"Confirmation has been reversed for {user.name} because they added new Pokémon.")

        # Fetch the user's Pokémon
        query = "SELECT * FROM users_pokemon WHERE userid = $1"
        user_pokemon = await self.db.fetch(query, user.id)

        if not user_pokemon:
            await ctx.send("You have no Pokémon to trade!")
            return

        # Get already added pokemon_ids in trade for this user
        existing_pokemon_ids = set()
        for entry in self.active_trades[trade_key][user.id]:
            if " • " in entry:
                id_part = entry.split(" • ")[0]
                if id_part.isdigit():
                    existing_pokemon_ids.add(int(id_part))

        filtered_pokemon = []
        for pokemon in user_pokemon:
            if pokemon["pokemon_id"] in existing_pokemon_ids:
                continue  # Already in trade

            if pokemon.get("favorite") or pokemon.get("selected"):
                continue  # Skip favorite or selected Pokémon

            if (
                    filter_shiny(pokemon, filters)
                    and filter_name(pokemon, filters)
                    and filter_total_iv(pokemon, filters)
                    and filter_stats(pokemon, filters)
                    and filter_rarity(pokemon, filters)
                    and filter_fusion(pokemon, filters)
            ):
                filtered_pokemon.append(pokemon)

        # Apply skip and limit filters
        filtered_pokemon = filter_skip(filtered_pokemon, filters, user_id, bot)
        filtered_pokemon = filter_limit(filtered_pokemon, filters, user_id, bot)

        if not filtered_pokemon:
            await ctx.send(
                "No new Pokémon matched the filters, were already in the trade, or are marked as favorite/selected!")
            return

        confirmation_message = await ctx.send(
            f"Are you sure you want to add **{len(filtered_pokemon)}** Pokémon to your current trade?"
        )
        await confirmation_message.add_reaction("✅")
        await confirmation_message.add_reaction("❌")

        def check(reaction, reacting_user):
            return (
                    reacting_user == ctx.author and
                    str(reaction.emoji) in ["✅", "❌"] and
                    reaction.message.id == confirmation_message.id
            )

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Trade addition timed out. No Pokémon were added.")
            return

        if str(reaction.emoji) == "❌":
            await ctx.send("Trade addition cancelled.")
            return

        # Add Pokémon to trade
        for pokemon in filtered_pokemon:
            shiny_prefix = "✨ " if pokemon["shiny"] else ""
            fusionable_prefix = "🧬 " if pokemon["fusionable"] else ""
            formatted_pokemon = (
                f"{pokemon['pokemon_id']} • {shiny_prefix}{fusionable_prefix}"
                f"{pokemon['pokemon_name']} • Lvl {pokemon['level']} • {pokemon['total_iv_percent']:.2f}%"
            )
            self.active_trades[trade_key][user.id].append(formatted_pokemon)

        # Update trade embed
        user1 = await ctx.guild.fetch_member(trade_key[0])
        user2 = await ctx.guild.fetch_member(trade_key[1])
        await self.send_trade_embed(
            ctx.channel,
            user1,
            user2,
            self.active_trades[trade_key],
            self.active_trades[trade_key]["confirmed"]
        )

        await ctx.send(f"Added {len(filtered_pokemon)} Pokémon to the trade.")


import re

def parse_filters(args):
    stat_mapping = {
        "atk": "attack", "def": "defense", "spatk": "spatk",
        "spdef": "spdef", "hp": "hp", "spd": "speed"
    }

    filters = {
        "shiny": False, "name": None, "iv": None, "stats": {},
        "limit": None, "skip": None, "legendary": False,
        "mythical": False, "ultrabeast": False, "rare": False,
        "fusionable": False, "event": False
    }

    args = list(args)
    parsed_args = {}

    print(f"🔹 Raw Args: {args}")  # Debug: Initial arguments

    while args:
        arg = args.pop(0).lower()
        print(f"➡️ Processing Arg: {arg}")  # Debug: Show each argument being processed

        if arg in ["--shiny", "--sh"]:
            parsed_args["shiny"] = True
            print(f"✔️ Set shiny = True")  # Debug: Shiny filter applied

        elif arg in ["--name", "--n"] and args:
            parsed_args["name"] = args.pop(0).lower()
            print(f"✔️ Set name = {parsed_args['name']}")  # Debug: Name filter applied

        elif arg == "--limit" and args:
            parsed_args["limit"] = int(args.pop(0))
            print(f"✔️ Set limit = {parsed_args['limit']}")  # Debug: Limit filter applied

        elif arg == "--skip" and args:
            parsed_args["skip"] = int(args.pop(0))
            print(f"✔️ Set skip = {parsed_args['skip']}")  # Debug: Skip filter applied

        elif arg in ["--rare"]:
            parsed_args["rare"] = True
            print(f"✔️ Set rare = True")  # Debug: Rare filter applied

        elif arg in ["--leg", "--legendary"]:
            parsed_args["legendary"] = True
            print(f"✔️ Set legendary = True")  # Debug: Legendary filter applied

        elif arg in ["--my", "--mythical"]:
            parsed_args["mythical"] = True
            print(f"✔️ Set mythical = True")  # Debug: Mythical filter applied

        elif arg in ["--ub", "--ultrabeast"]:
            parsed_args["ultrabeast"] = True
            print(f"✔️ Set ultrabeast = True")  # Debug: Ultra Beast filter applied

        elif arg in ["--ev", "--event"]:
            parsed_args["event"] = True
            print(f"✔️ Set event = True")

        elif arg in ["--fn", "--fusionable"]:
            parsed_args["fusionable"] = True
            print("✔️ Set fusionable = True")


        elif arg == "--iv" and args:
            iv_match = re.match(r'([<>]=?|=)?(\d+)', args[0])
            if iv_match:
                op, value = iv_match.groups()
                parsed_args["iv"] = (op or "=", int(value))
                args.pop(0)
                print(f"✔️ Set IV filter: {parsed_args['iv']}")  # Debug: IV filter applied



        elif arg.startswith("--"):
            match = re.match(r"--([a-z]+)([<>=]{1,2})(\d+)", arg)
            if match:
                stat_key, op, value = match.groups()
                if stat_key in stat_mapping:
                    stat = stat_mapping[stat_key]
                    parsed_args.setdefault("stats", {})[stat] = (op, int(value))
                    print(f"✔️ Set {stat} filter: {parsed_args['stats'][stat]}")  # Debu
            elif args:
                stat_key = arg[2:]
                if stat_key in stat_mapping:
                    stat = stat_mapping[stat_key]
                    stat_match = re.match(r'([<>]=?|=)?(\d+)', args[0])
                    if stat_match:
                        op, value = stat_match.groups()
                        parsed_args.setdefault("stats", {})[stat] = (op or "=", int(value))
                        args.pop(0)
                        print(f"✔️ Set {stat} filter: {parsed_args['stats'][stat]}")  # Debug
    # Debug: Stat filter applied

    # Ensure "shiny" filter is always updated properly
    filters["shiny"] = parsed_args.get("shiny", False)
    filters.update(parsed_args)

    # Final Debug Print
    print("✅ Final Parsed Filters:", filters)

    return filters



class Trade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trade_system = TradeSystem(bot.db)  # Pass the database connection

    @commands.command(name="trade", aliases=["t"])
    async def trade(self, ctx, member: discord.Member):
        await self.trade_system.start_trade(ctx, ctx.author, member)

    @commands.command(name="trade_add", aliases=["ta"])
    async def trade_add(self, ctx, *, item):
        await self.trade_system.add_trade_item(ctx, ctx.author, item)

    @commands.command(name="trade_confirm", aliases=["tc"])
    async def trade_confirm(self, ctx):
        await self.trade_system.confirm_trade(ctx, ctx.author)

    @commands.command(name="trade_cancel", aliases=["tx"])
    async def trade_cancel(self, ctx):
        await self.trade_system.cancel_trade(ctx, ctx.author)

    @commands.command(name="trade_remove", aliases=["tr"])
    async def trade_remove(self, ctx, *, item):
        await self.trade_system.remove_trade_item(ctx, ctx.author, item)

    @commands.command(name="trade_addall", aliases=["taa"])
    async def trade_add_all_cmd(self, ctx, *, filters: str):
        """Add all Pokémon matching the filters to the trade."""
        user = ctx.author

        # Convert filter string into a list of arguments
        filter_args = filters.split()  # Example: "--shiny --iv >80" → ["--shiny", "--iv", ">80"]
        parsed_filters = parse_filters(filter_args)

        # Call trade_add_all from TradeSystem
        await self.trade_system.trade_add_all(ctx, user, parsed_filters)
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.emoji in ["⬅️", "➡️"]:
            await self.trade_system.handle_pagination(reaction, user)


async def setup(bot):
   await bot.add_cog(Trade(bot))


