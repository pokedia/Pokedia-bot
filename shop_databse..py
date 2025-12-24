import json
import os

DATABASE_FILE = "shop_database.json"

# Load or initialize the database
def load_database():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w") as f:
            json.dump({}, f)
    with open(DATABASE_FILE, "r") as f:
        return json.load(f)

# Save the database
def save_database(data):
    with open(DATABASE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Add items to a user's inventory
def add_item(user_id, item, amount):
    data = load_database()
    if user_id not in data:
        data[user_id] = {"shards": 0, "redeems": 0, "incense": 0}

    if item in data[user_id]:
        data[user_id][item] += amount
    else:
        return False  # Invalid item

    save_database(data)
    return True

# Get a user's inventory
def get_inventory(user_id):
    data = load_database()
    return data.get(user_id, {"shards": 0, "redeems": 0, "incense": 0})

# Example Usage:
# add_item("123456", "shards", 10)
# print(get_inventory("123456"))
