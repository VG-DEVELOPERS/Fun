from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import collection, application


# /char command
async def char_command(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        return await update.message.reply_text("❗ Usage: /char <character name or part of it>")

    query = " ".join(args)
    regex = {"$regex": query, "$options": "i"}
    characters = await collection.find({"name": regex}, {"_id": 0}).to_list(length=100)

    if not characters:
        return await update.message.reply_text("❌ No characters found with that name.")

    context.chat_data["char_list"] = characters
    context.chat_data["char_index"] = 0
    await show_character(update, context, new=True)


# Show character with photo + caption + buttons
async def show_character(update: Update, context: CallbackContext, new=False):
    index = context.chat_data.get("char_index", 0)
    char_list = context.chat_data.get("char_list", [])

    if not char_list:
        return

    char = char_list[index]

    caption = (
        f"🪭 <b>{char.get('name')}</b>\n"
        f"🌍 <b>Series:</b> {char.get('anime')}\n"
        f"🏆 <b>Rarity:</b> {char.get('rarity')}\n"
        f"🎴 <b>ID:</b> {char.get('id')}"
    )

    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data="char_prev"))
    if index < len(char_list) - 1:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data="char_next"))

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None
    media = InputMediaPhoto(media=char.get("img_url"), caption=caption, parse_mode="HTML")

    if new:
        await update.message.reply_photo(
            photo=char.get("img_url"),
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_media(media=media)
        await query.edit_message_reply_markup(reply_markup=keyboard)


# Callback for navigation
async def char_callback(update: Update, context: CallbackContext):
    action = update.callback_query.data
    index = context.chat_data.get("char_index", 0)
    char_list = context.chat_data.get("char_list", [])

    if not char_list:
        return

    if action == "char_next":
        index += 1
    elif action == "char_prev":
        index -= 1

    index = max(0, min(index, len(char_list) - 1))
    context.chat_data["char_index"] = index

    await show_character(update, context, new=False)


# Register handlers
application.add_handler(CommandHandler("char", char_command, block=False))
application.add_handler(CallbackQueryHandler(char_callback, pattern=r"^char_(next|prev)$", block=False))
    
