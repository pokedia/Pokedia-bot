import discord
from discord.ext import commands
import uuid

class Convert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="convert", invoke_without_command=True)
    async def convert(self, ctx):
        await ctx.send(
            "Available subcommands:\n"
            "`p!convert cash <amount>` - Convert Pokécash to bosscoins\n"
            "`p!convert redeem <amount>` - Convert Redeems to bosscoins\n"
            "`p!convert pokemon <id>` - Transfer Pokémon to main Pokémon table"
        )

    @convert.command(name="cash")
    async def convert_cash(self, ctx, amount: int):
        await self._convert_resource(ctx, amount, "pokecash")

    @convert.command(name="redeem")
    async def convert_redeem(self, ctx, amount: int):
        await self._convert_resource(ctx, amount, "redeems")

    async def _convert_resource(self, ctx, amount: int, column: str):
        if amount <= 0:
            return await ctx.send("Amount must be greater than 0.")

        user_id = ctx.author.id

        # Fetch current resource (pokecash or redeems)
        row = await self.bot.db.fetchrow(
            f"SELECT {column} FROM users WHERE userid = $1", user_id
        )
        if not row:
            return await ctx.send("You are not registered in the database.")

        current_balance = row[column]
        if current_balance < amount:
            return await ctx.send(f"You don't have enough {column} to convert.")

        # Subtract the resource
        await self.bot.db.execute(
            f"UPDATE users SET {column} = {column} - $1 WHERE userid = $2",
            amount, user_id
        )

        # Build SQL log query
        if column == "redeems":
            sql_query = (
                f"UPDATE bosscoins SET redeem = redeem + {amount} "
                f"WHERE user_id = {user_id};"
            )
        else:
            sql_query = (
                f"UPDATE bosscoins SET balance = balance + {amount} "
                f"WHERE user_id = {user_id};"
            )

        # Send SQL to bosscoins logging channel
        sql_channel_id = 1373707342121664635
        sql_channel = self.bot.get_channel(sql_channel_id)
        if sql_channel:
            await sql_channel.send(f"```sql\n{sql_query}\n```")

        await ctx.send(f"✅ Converted {amount} {column}.")

    @convert.command(name="pokemon")
    async def convert_pokemon(self, ctx, *poke_ids: int):
        user_id = ctx.author.id

        if not poke_ids:
            return await ctx.send("❌ Please provide at least one Pokémon ID to convert.")

        sql_channel_id = 1373707342121664635
        sql_channel = self.bot.get_channel(sql_channel_id)

        success_ids = []
        failed_ids = []

        for poke_id in poke_ids:
            # Fetch the Pokémon data
            row = await self.bot.db.fetchrow(
                "SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                user_id, poke_id
            )

            if not row:
                failed_ids.append(poke_id)
                continue

            # Prepare SQL insert
            columns = list(row.keys())
            values = [row[col] for col in columns]

            column_list = ', '.join(columns)

            def format_value(v):
                if v is None:
                    return 'NULL'
                if isinstance(v, bool):
                    return 'TRUE' if v else 'FALSE'
                if isinstance(v, str):
                    return "'" + v.replace("'", "''") + "'"
                if isinstance(v, uuid.UUID):
                    return f"'{str(v)}'::uuid"
                return str(v)

            value_list = ', '.join(format_value(v) for v in values)
            insert_sql = f"INSERT INTO pokemon ({column_list}) VALUES ({value_list});"

            # Send individual SQL to the logging channel
            if sql_channel:
                await sql_channel.send(f"```sql\n{insert_sql}\n```")

            # Delete the Pokémon from the table
            await self.bot.db.execute(
                "DELETE FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                user_id, poke_id
            )

            success_ids.append(poke_id)

        # Final summary message to the user
        summary = []
        if success_ids:
            summary.append(f"✅ Converted and removed Pokémon ID(s): {', '.join(map(str, success_ids))}.")
        if failed_ids:
            summary.append(f"❌ No Pokémon found with ID(s): {', '.join(map(str, failed_ids))}.")

        await ctx.send("\n".join(summary))

    @convert.error
    async def convert_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                "❌ Invalid subcommand.\n"
                "Use:\n"
                "`p!convert cash <amount>` - Convert Pokécash\n"
                "`p!convert redeem <amount>` - Convert Redeems\n"
                "`p!convert pokemon <id>` - Transfer Pokémon"
            )

async def setup(bot):
    await bot.add_cog(Convert(bot))


