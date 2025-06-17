from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from shivu import collection, application 

# `/char <anime name>` command
async def char_command(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        return await update.message.reply_text("❗ Usage: /char <anime name or part of it>")

    query_text = " ".join(args).strip()
    regex = {"$regex": query_text, "$options": "i"}
    matches = await collection.find(
        {"anime": regex},
        {"_id": 0}
    ).to_list(length=100)

    if not matches:
        return await update.message.reply_text("❌ No characters found with that anime.")

    # Attach matches in chat data
    chat_id = update.effective_chat.id
    context.chat_data.setdefault("char_list", {})[chat_id] = {
        "results": matches,
        "index": 0
    }

    return await show_char_page(update, context, chat_id, 0)

# Helper to show a character page
async def show_char_page(update: Update, context: CallbackContext, chat_id: int, idx: int):
    data = context.chat_data["char_list"].get(chat_id)
    if not data:
        return

    results, index = data["results"], idx
    character = results[index]
    msg_text = (
        f"🪭 <b>{character['name']}</b>\n"
        f"🌍 <b>{character['anime']}</b>\n"
        f"🏆 <b>Rarity:</b> {character['rarity']}\n"
        f"🎴 <b>ID:</b> {character['id']}"
    )

    keyboard = []
    if index > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"char_{chat_id}_{index-1}"))
    if index < len(results) - 1:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"char_{chat_id}_{index+1}"))

    media = character.get("img_url") or character.get("file_id")
    if not media:
        return await update.message.reply_text("⚠️ Media for this character is missing!")

    if update.callback_query:
        await update.callback_query.edit_message_media(
            media=character_image(media),
            reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None,
        )
        await update.callback_query.edit_message_caption(msg_text, parse_mode="HTML")
    else:
        await update.message.reply_photo(
            photo=media,
            caption=msg_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None
        )

def character_image(url):
    from telegram import InputMediaPhoto
    return InputMediaPhoto(media=url)

# ```callback_query``` handler
async def char_button(update: Update, context: CallbackContext):
    query = update.callback_query
    _, chat_id_str, idx_str = query.data.split("_")
    chat_id, idx = int(chat_id_str), int(idx_str)
    await show_char_page(update, context, chat_id, idx)

# Add handlers
application.add_handler(CommandHandler("char", char_command, block=False))
application.add_handler(CallbackQueryHandler(char_button, pattern=r"^char_\d+_\d+$", block=False))
  
