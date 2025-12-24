def update_balance(db, user_id, pokecash_delta=0, shards_delta=0):
    """Updates the balance for a user in the database, initializing fields if needed."""
    # Get the user data or initialize it if it doesn't exist
    user_data = db.get_user(user_id)
    if not user_data:
        user_data = {"pokemon": [], "pokecash": 0, "shards": 0}

    # Ensure fields exist in the user data
    if "pokecash" not in user_data:
        user_data["pokecash"] = 0
    if "shards" not in user_data:
        user_data["shards"] = 0

    # Update the balance
    user_data["pokecash"] += pokecash_delta
    user_data["shards"] += shards_delta

    # Save the updated user data back to the database
    db.update_user(user_id, user_data)

def get_user_balance(db, user_id):
    """Retrieves the balance for a user from the database."""
    user_data = db.get_user(user_id)
    if not user_data:
        return {"pokecash": 0, "shards": 0}  # Default balance if the user doesn't exist
    return {
        "pokecash": user_data.get("pokecash", 0),
        "shards": user_data.get("shards", 0)
    }

def format_number(value):
    """Formats a number with commas."""
    return f"{value:,}"
