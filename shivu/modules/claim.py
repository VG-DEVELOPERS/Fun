import asyncio
from pyrogram import filters, Client, types as t
from pyrogram.types import Message
from shivu import shivuu as bot
from shivu import user_collection, collection
import time
from datetime import datetime, timedelta

DEVS = (7717913705)

async def get_unique_characters(receiver_id, target_rarities=['⚪ Common', '🟣 Rare', '🟡 Legendary']):
    try:
        pipeline = [
            {'$match': {'rarity': {'$in': target_rarities}, 'id': {'$nin': [char['id'] for char in (await user_collection.find_one({'id': receiver_id}, {'characters': 1}))['characters']]}}},
            {'$sample': {'size': 1}}  # Adjust Num
        ]

        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=None)
        return characters
    except Exception as e:
        return []

# Dictionary to store last claim time for each user
last_claim_time = {}

@bot.on_message(filters.command(["hclaim"]))
async def hclaim(_, message: t.Message):
    chat_id = message.chat.id
    mention = message.from_user.mention
    user_id = message.from_user.id

    # Check if the user is banned
    if user_id == 7162166061:
        return await message.reply_text(f"Sorry {mention}, you are banned from using this command.")

    # Check if the user has already claimed a waifu today
    now = datetime.now()
    if user_id in last_claim_time:
        last_claim_date = last_claim_time[user_id]
        if last_claim_date.date() == now.date():
            next_claim_time = (last_claim_date + timedelta(days=1)).strftime("%H:%M:%S")
            return await message.reply_text(f"𝑲𝒂𝒍 𝑨𝒏𝒂 𝑲𝒂𝒍 😂", quote=True)

    # Update the last claim time for the user
    last_claim_time[user_id] = now

    receiver_id = message.from_user.id
    unique_characters = await get_unique_characters(receiver_id)
    try:
        await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': {'$each': unique_characters}}})
        img_urls = [character['img_url'] for character in unique_characters]
        captions = [
            f"𝑪𝒐𝒏𝒈𝒓𝒂𝒕𝒖𝒍𝒂𝒕𝒊𝒐𝒏𝒔 🎊 {mention}! 𝒀𝒐𝒖 𝒈𝒐𝒕 𝒀𝒐𝒖𝒓 𝒏𝒆𝒘 𝒅𝒂𝒊𝒍𝒚 ✨\n"
            f"🎀 𝑵𝑨𝑴𝑬: {character['name']}\n"
            f"⚕️ 𝑹𝑨𝑹𝑰𝑻𝒀: {character['rarity']}\n"
            f"⚜️ 𝑨𝑵𝑰𝑴𝑬: {character['anime']}\n"

            f"𝑪𝒐𝒎𝒆 𝒂𝒈𝒂𝒊𝒏 𝑻𝒐𝒎𝒐𝒓𝒓𝒐𝒘 𝒇𝒐𝒓 𝒚𝒐𝒖𝒓 𝒏𝒆𝒙𝒕 𝒄𝒍𝒂𝒊𝒎 🍀\n"
            for character in unique_characters
        ]
        for img_url, caption in zip(img_urls, captions):
            await message.reply_photo(photo=img_url, caption=caption)
    except Exception as e:
        print(e)

@bot.on_message(filters.command(["hfind"]))
async def hfind(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("🔖 Please provide the ID ☘️", quote=True)
    
    waifu_id = message.command[1]
    waifu = await collection.find_one({'id': waifu_id})

    if not waifu:
        return await message.reply_text("🎗️ No character found with that ID ❌", quote=True)

    # Fetch top collectors
    top_users = await user_collection.aggregate([
        {'$match': {'characters.id': waifu_id}},
        {'$unwind': '$characters'},
        {'$match': {'characters.id': waifu_id}},
        {'$group': {'_id': '$id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]).to_list(length=10)

    usernames = []
    for user_info in top_users:
        user_id = user_info['_id']
        try:
            user = await bot.get_users(user_id)
            usernames.append(f"@{user.username}" if user.username else f"➥ {user_id}")
        except Exception:
            usernames.append(f"➥ {user_id}")

    caption = (
        f"🧩 𝑰𝒏𝒇𝒐𝒓𝒎𝒂𝒕𝒊𝒐𝒏:\n"
        f"🪭 𝑵𝒂𝒎𝒆: {waifu['name']}\n"
        f"⚕️ 𝑹𝒂𝒓𝒊𝒕𝒚: {waifu['rarity']}\n"
        f"⚜️ 𝑨𝒏𝒊𝒎𝒆: {waifu['anime']}\n"
        f"🪅 𝑰𝑫: {waifu['id']}\n\n"
        f"✳️ 𝑻𝒐𝒑 𝑼𝒔𝒆𝒓𝒔 𝒘𝒊𝒕𝒉 𝒕𝒉𝒊𝒔 𝒘𝒂𝒊𝒇𝒖:\n\n"
    )

    for i, user_info in enumerate(top_users):
        caption += f"{i+1}. {usernames[i]} x{user_info['count']}\n"

    # Detect media
    file = waifu.get('file_id') or waifu.get('img_url')
    media_type = waifu.get('media_type', 'photo')

    if not file:
        return await message.reply_text("⚠️ No image or video found for this character.")

    if media_type == "video":
        await message.reply_video(video=file, caption=caption)
    else:
        await message.reply_photo(photo=file, caption=caption)
        
@bot.on_message(filters.command(["cfind"]))
async def cfind(_, message: t.Message):
    if len(message.command) < 2:
        return await message.reply_text("𝑷𝒍𝒆𝒂𝒔𝒆 𝒑𝒓𝒐𝒗𝒊𝒅𝒆 𝒕𝒉𝒆 𝒂𝒏𝒊𝒎𝒆 𝒏𝒂𝒎𝒆✨", quote=True)

    anime_name = " ".join(message.command[1:])
    characters = await collection.find({'anime': anime_name}).to_list(length=None)
    
    if not characters:
        return await message.reply_text(f"𝑵𝒐 𝒄𝒉𝒂𝒓𝒂𝒄𝒕𝒆𝒓𝒔 𝒇𝒐𝒖𝒏𝒅 𝒇𝒓𝒐𝒎 𝒕𝒉𝒆 𝒂𝒏𝒊𝒎𝒆 ❎ {anime_name}.", quote=True)

    captions = [
        f"🎏 𝑵𝒂𝒎𝒆: {char['name']}\n🪅 𝑰𝑫: {char['id']}\n🧩 𝑹𝒂𝒓𝒊𝒕𝒚: {char['rarity']}\n"
        for char in characters
    ]
    response = "\n".join(captions)
    await message.reply_text(f"🍁 𝑪𝒉𝒂𝒓𝒂𝒄𝒕𝒆𝒓𝒔 𝒇𝒓𝒐𝒎 {anime_name}:\n\n{response}", quote=True)
