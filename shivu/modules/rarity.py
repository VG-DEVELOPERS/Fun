from pyrogram import Client, filters
from pyrogram.types import Message
from shivu import collection, shivuu as shivuu  # Assuming collection is your MongoDB collection

rarity_map = {
    "1": "⚪ Common",
    "2": "🟣 Rare",
    "3": "🟡 Legendary",
    "4": "🟢 Medium",
    "5": "🔮 limited edition",
    "6": "⚜️ premium",
    "7": "🎴 universal",

}

    



@shivuu.on_message(filters.command("rarity"))
async def rarity_count(client: Client, message: Message):
    try:
        rarity_counts = {}

        # Count the characters by rarity
        for rarity_id, rarity_name in rarity_map.items():
            count = await collection.count_documents({'rarity': rarity_name})
            rarity_counts[rarity_name] = count

        # Create the message with the rarity counts
        rarity_message = "📊 𝗥𝗮𝗿𝗶𝘁𝘆 𝗖𝗼𝘂𝗻𝘁 📊\n\n"
        for rarity_name, count in rarity_counts.items():
            rarity_message += f"{rarity_name}: {count} characters\n"

        await message.reply_text(rarity_message)

    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
