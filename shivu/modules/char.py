from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import collection, application

# /char command — search by character name (partial match)
async def char_command(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        return await update.message.reply_text("❗ Usage: /char <character name or part of it>")

    query_text = " ".join(args).strip()
    regex = {"$regex": query_text, "$options": "i"}
    matches = await collection.find(
        {"name": regex},
        {"_id": 0}
    ).to_list(length=100)

    if not matches:
        return await update.message.reply_text("❌ No characters found with that name.")

    chat_id = update.effective_chat.id
    context.chat_data["char_list"] = matches
    context.chat_data["char_index"] = 0

    return await show_char_page(update, context, new_query=True)

# Helper to show a character page, either initial or callback
async def show_char_page(update: Update, context: CallbackContext, new_query=False):
    characters = context.chat_data.get("char_list", [])
    idx = context.chat_data.get("char_index", 0)

    if idx < 0 or idx >= len(characters):
        return

    char = characters[idx]
    caption = (
        f"🪭 <b>{char['name']}</b>\n"
        f"🌍 <b>Series:</b> {char.get('anime','N/A')}\n"
        f"🏆 <b>Rarity:</b> {char.get('rarity','N/A')}\n"
        f"🎴 <b>ID:</b> {char.get('id')}"
    )

    keyboard = []
    if idx > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Prev", callback_data="char_prev"))
    if idx < len(characters) - 1:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data="char_next"))

    media = char.get("img_url") or char.get("file_id")
    if not media:
        return await update.message.reply_text("⚠️ This character has no media.")

    markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

    if new_query:
        await update.message.reply_photo(photo=media, caption=caption, parse_mode="HTML", reply_markup=markup)
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_media(media=InputMediaPhoto(media=media), reply_markup=markup)
        await query.edit_message_caption(caption=caption, parse_mode="HTML")

# Callback handler for navigation buttons
async def char_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    action = query.data  # "char_prev" or "char_next"
    idx = context.chat_data.get("char_index", 0)

    if action == "char_prev":
        idx -= 1
    elif action == "char_next":
        idx += 1

    context.chat_data["char_index"] = max(0, min(idx, len(context.chat_data.get("char_list", [])) - 1))
    await show_char_page(update, context, new_query=False)

# Register handlers
application.add_handler(CommandHandler("char", char_command, block=False))
application.add_handler(CallbackQueryHandler(char_callback, pattern="^char_(prev|next)$", block=False))
