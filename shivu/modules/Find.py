from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import collection, application 

async def find_char(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Please provide the character ID.\nExample: /find 01")
        return

    char_id = context.args[0]
    character = await collection.find_one({"id": char_id})

    if not character:
        await update.message.reply_text("❌ Character not found.")
        return

    name = character.get("name", "Unknown")
    anime = character.get("anime", "Unknown")
    rarity = character.get("rarity", "Unknown")
    file_id = character.get("file_id") or character.get("img_url")
    media_type = character.get("media_type", "photo")

    caption = (
        f"<b>🧩 Character Info</b>\n"
        f"<b>🪭 Name:</b> {name}\n"
        f"<b>⚜️ Anime:</b> {anime}\n"
        f"<b>✨ Rarity:</b> {rarity}\n"
        f"<b>🆔 ID:</b> {char_id}"
    )

    try:
        if media_type == "photo":
            await update.message.reply_photo(photo=file_id, caption=caption, parse_mode="HTML")
        elif media_type == "video":
            await update.message.reply_video(video=file_id, caption=caption, parse_mode="HTML")
        else:
            await update.message.reply_text(caption, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error sending media: {e}")
        
FIND_HANDLER = CommandHandler('find', find_char, block=False)
application.add_handler(FIND_HANDLER)
