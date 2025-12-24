import asyncpg
import asyncio

class Database:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        """Establish a connection pool with PostgreSQL."""
        if not self.pool:  # Ensure only one connection pool is created
            self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()

    async def get_user(self, user_id):
        print(f"🔥 DEBUG: get_user() called for user {user_id}")  # Debugging print
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE userid = $1", user_id)
            if not user:
                await conn.execute("INSERT INTO users (userid, pokecash, shards, redeems) VALUES ($1, 0, 0, 0)",
                                   user_id)
                return {"pokecash": 0, "shards": 0, "redeems": 0}
            return dict(user)

    async def update_user(self, user_id, pokecash, shards, redeems):
        """Update user currency values."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET pokecash = $2, shards = $3, redeems = $4 WHERE userid = $1
                """,
                user_id, pokecash, shards, redeems
            )

    async def add_pokemon(self, user_id, pokemon_id, xp, name, level, total_iv, ivs, stats, shiny, fusionable, selected,
                          favorite, caught):
        """Add a Pokémon to a user's collection."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users_pokemon (userid, pokemon_id, xp, pokemon_name, level, total_iv_percent, hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                                          hp, attack, defense, spatk, spdef, speed, shiny, fusionable, selected, favorite, caught)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                """,
                user_id, pokemon_id, xp, name, level, total_iv, *ivs, *stats, shiny, fusionable, selected, favorite, caught
            )

    async def get_pokemon(self, user_id, pokemon_id):
        """Retrieve a Pokémon by its ID."""
        async with self.pool.acquire() as conn:
            pokemon = await conn.fetchrow("SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2", user_id, pokemon_id)
            return dict(pokemon) if pokemon else None

    async def transfer_pokemon(self, from_user_id, to_user_id, pokemon_id):
        """Transfer a Pokémon from one user to another."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Retrieve the Pokémon's data
                pokemon = await conn.fetchrow("SELECT * FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2",
                                              from_user_id, pokemon_id)
                if pokemon:
                    # Get the maximum pokemon_id for the target user and increment it by 1
                    new_pokemon_id = await conn.fetchval(
                        "SELECT COALESCE(MAX(pokemon_id), 0) + 1 FROM users_pokemon WHERE userid = $1", to_user_id)

                    # Prepare the data for insertion with the new user ID
                    result = await conn.execute(
                        """
                        INSERT INTO users_pokemon (userid, pokemon_id, xp, pokemon_name, level, total_iv_percent,
                                                    hp_iv, attack_iv, defense_iv, spatk_iv, spdef_iv, speed_iv,
                                                    hp, attack, defense, spatk, spdef, speed, shiny, fusionable,
                                                    selected, favorite, caught, unique_id, max_xp, nickname)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26)
                        """,
                        to_user_id, new_pokemon_id, pokemon['xp'], pokemon['pokemon_name'], pokemon['level'],
                        pokemon['total_iv_percent'], pokemon['hp_iv'], pokemon['attack_iv'], pokemon['defense_iv'],
                        pokemon['spatk_iv'], pokemon['spdef_iv'], pokemon['speed_iv'], pokemon['hp'],
                        pokemon['attack'], pokemon['defense'], pokemon['spatk'], pokemon['spdef'], pokemon['speed'],
                        pokemon['shiny'], pokemon['fusionable'], pokemon['selected'], pokemon['favorite'],
                        False,  # Setting 'caught' to False
                        pokemon['unique_id'], pokemon['max_xp'], pokemon['nickname']
                    )
                    # Delete the Pokémon from the original user's collection
                    await conn.execute("DELETE FROM users_pokemon WHERE userid = $1 AND pokemon_id = $2", from_user_id,
                                       pokemon_id)
                    return True
        return False

    async def transfer_cash(self, from_user_id, to_user_id, amount):
        """Transfer cash from one user to another."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                from_user = await conn.fetchrow("SELECT pokecash FROM users WHERE userid = $1", from_user_id)
                if from_user and from_user["pokecash"] >= amount:
                    await conn.execute("UPDATE users SET pokecash = pokecash - $1 WHERE userid = $2", amount, from_user_id)
                    await conn.execute("UPDATE users SET pokecash = pokecash + $1 WHERE userid = $2", amount, to_user_id)
                    return True
        return False

    async def transfer_redeems(self, from_user_id, to_user_id, amount):
        """Transfer redeems from one user to another."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                from_user = await conn.fetchrow("SELECT redeems FROM users WHERE userid = $1", from_user_id)
                if from_user and from_user["redeems"] >= amount:
                    await conn.execute("UPDATE users SET redeems = redeems - $1 WHERE userid = $2", amount, from_user_id)
                    await conn.execute("UPDATE users SET redeems = redeems + $1 WHERE userid = $2", amount, to_user_id)
                    return True
        return False

    async def execute(self, query, *args):
        """Execute a query that doesn't return data (INSERT, UPDATE, DELETE)."""
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)  # Fetch multiple rows

    async def fetchrow(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)  # Fetch a single row

    async def fetchval(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)  # Fetch a single value

    async def update_pokemon(self, user_id, pokemon_id, pokemon_data):
        query = """
        UPDATE users_pokemon
        SET 
            caught = $1,
            userid = $2,
            xp = $3,
            max_xp = $4,
            pokemon_name = $5,
            level = $6,
            total_iv_percent = $7,
            hp_iv = $8,
            attack_iv = $9,
            defense_iv = $10,
            spatk_iv = $11,
            spdef_iv = $12,
            speed_iv = $13,
            hp = $14,
            attack = $15,
            defense = $16,
            spatk = $17,
            spdef = $18,
            speed = $19
        WHERE userid = $2 AND pokemon_id = $3
        """

        await self.pool.execute(query,
                                pokemon_data['caught'],
                                pokemon_data['user_id'],
                                pokemon_data['xp'],
                                pokemon_data['max_xp'],
                                pokemon_data['pokemon_name'],
                                pokemon_data['level'],
                                pokemon_data['total_iv_percent'],
                                pokemon_data['hp_iv'],
                                pokemon_data['attack_iv'],
                                pokemon_data['defense_iv'],
                                pokemon_data['spatk_iv'],
                                pokemon_data['spdef_iv'],
                                pokemon_data['speed_iv'],
                                pokemon_data['hp'],
                                pokemon_data['attack'],
                                pokemon_data['defense'],
                                pokemon_data['spatk'],
                                pokemon_data['spdef'],
                                pokemon_data['speed'],
                                )


# Create a single global database instance
db = Database("postgresql://postgres:pokedia2389@localhost/pokedia")

# Function to initialize the database at bot startup
async def setup_database():
    await db.connect()

# Function to get the database pool (so other files can use it)
async def get_database_pool():
    """Returns the database pool from the Database instance."""
    if not db.pool:
        await db.connect()
    return db.pool
