from pyrogram import Client, filters
from pyrogram.types import Message
from shivu import collection  # MongoDB collection you store characters in

@Client.on_message(filters.command("find"))
async def find_character(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❗ Please provide a character ID.")

    char_id = message.command[1]

    try:
        character = await collection.find_one({"id": char_id})
    except Exception as e:
        return await message.reply_text(f"❌ Database error: {e}")

    if not character:
        return await message.reply_text("❌ No character found with that ID.")

    name = character.get("name", "N/A")
    anime = character.get("anime", "N/A")
    rarity = character.get("rarity", "N/A")
    media_type = character.get("media_type", "photo")
    file_id = character.get("file_id") or character.get("img_url")

    caption = (
        f"🧩 <b>Character Info:</b>\n"
        f"🪭 <b>Name:</b> {name}\n"
        f"⚜️ <b>Anime:</b> {anime}\n"
        f"✨ <b>Rarity:</b> {rarity}\n"
        f"🪅 <b>ID:</b> {char_id}"
    )

    if not file_id:
        return await message.reply_text("⚠️ No media associated with this character.")

    try:
        if media_type == "photo":
            await message.reply_photo(file_id, caption=caption, parse_mode="html")
        elif media_type == "video":
            await message.reply_video(file_id, caption=caption, parse_mode="html")
        else:
            await message.reply_text(caption, parse_mode="html")
    except Exception as e:
        await message.reply_text(f"⚠️ Failed to send media.\n\n{e}")
