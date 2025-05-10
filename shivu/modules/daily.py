import random
import html
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from Grabber import user_collection, collection, Grabberu as app

# Allowed group ID (Only works in this group)
ALLOWED_GROUP_ID = -1002411662634  # Replace with your group's ID

# Rarity probability for waifu claims
RARITY_WEIGHTS = {
    '⚪ Common': 2,
    '🟢 Medium': 3,
    '🟠 Rare': 5,
    '🟡 Legendary': 90
}

async def get_random_waifu():
    """Fetch a random waifu from the database based on rarity probability."""
    selected_rarity = random.choices(
        list(RARITY_WEIGHTS.keys()), weights=RARITY_WEIGHTS.values(), k=1
    )[0]

    waifu = await collection.aggregate([
        {'$match': {'rarity': selected_rarity}},  
        {'$sample': {'size': 1}}  
    ]).to_list(length=1)

    return waifu[0] if waifu else None

@app.on_message(filters.command("claim"))
async def claim_waifu(client: Client, message: Message):
    """Allows users to claim a waifu only in the allowed group."""
    user_id = message.from_user.id
    first_name = html.escape(message.from_user.first_name)
    mention = f"[{first_name}](tg://user?id={user_id})"

    # Check if the command is used in a private chat
    if message.chat.type == "private":
        return await message.reply_text(
            "🔒 **You can only claim HUSBANDO in the group!**\n"
            "Join here to claim: [Seal W/H Group](https://t.me/+narH1LRo2EBjYjE1)"
        )

    # Ensure the command is used in the correct group
    if message.chat.id != ALLOWED_GROUP_ID:
        return await message.reply_text(
            "🚫 **This command only works in the official group!**\n"
            "Join here: [Seal W/H Group](https://t.me/seal_Your_WH_Group)"
        )

    # Fetch user data from the database
    user_data = await user_collection.find_one({'id': user_id})
    now_ist = datetime.utcnow().astimezone().strftime("%Y-%m-%d")

    if not user_data:
        user_data = {
            'id': user_id,
            'first_name': first_name,
            'characters': [],
            'waifu_count': 0,
            'last_claim_date': None
        }
        await user_collection.insert_one(user_data)

    # Check if user has already claimed today
    if user_data.get('last_claim_date') == now_ist:
        return await message.reply_text("⏳ **You have already claimed a HUSBANDO today! Try again tomorrow.**")

    # Get a random waifu
    waifu = await get_random_waifu()
    if not waifu:
        return await message.reply_text("⚠️ No HUSBANDO available at the moment. Try again later!")

    # Store waifu claim and update last claim date
    waifu_data = {
        'id': waifu['id'],
        'name': waifu['name'],
        'anime': waifu['anime'],
        'rarity': waifu['rarity'],
        'img_url': waifu.get('img_url', ''),
        'vid_url': waifu.get('vid_url', '')
    }

    await user_collection.update_one(
        {'id': user_id},
        {
            '$set': {'last_claim_date': now_ist},
            '$push': {'characters': waifu_data},  
            '$inc': {'waifu_count': 1}  
        }
    )

    # Prepare response message
    media_url = waifu.get('img_url') or waifu.get('vid_url')
    caption = (
        f"{mention} 🎉 You have claimed a HUSBANDO!\n"
        f"🎐 **Name:** {waifu['name']}\n"
        f"🐙 **Rarity:** {waifu['rarity']}\n"
        f"💮 **Anime:** {waifu['anime']}\n"
    )

    # Send media (image/video) or fallback to text
    try:
        if media_url:
            if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):  
                await message.reply_photo(photo=media_url, caption=caption)
            elif media_url.endswith(('.mp4', '.mov', '.avi', '.webm')):  
                await message.reply_video(video=media_url, caption=caption)
        else:
            await message.reply_text(caption)
    except Exception as e:
        print(f"Failed to send media: {e}")
        await message.reply_text(caption)
        
