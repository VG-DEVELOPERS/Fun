from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from shivu import db, application

global_settings = db.global_settings  # MongoDB collection

ALL_RARITIES = [
    "⚪ Common", "🟣 Rare", "🟡 Legendary", "🟢 Medium", "🔮 limited edition",
    "⚜️ premium", "🎴 universal", "🎐 Crystal", "🎊 Festival",
    "❄️ Winter", "🌞 Summer", "🍁 Autumn", "🌫️ Mist"
]

async def toggle_rarity_menu(update: Update, context: CallbackContext):
    if update.effective_user.id not in [OWNER_ID]:  # replace OWNER_ID with your Telegram ID
        await update.message.reply_text("Only the bot owner can use this command.")
        return

    settings = await global_settings.find_one({"_id": "rarity_config"}) or {"enabled_rarities": []}
    enabled = settings["enabled_rarities"]

    keyboard = []
    for rarity in ALL_RARITIES:
        status = "✅" if rarity in enabled else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {rarity}", callback_data=f"toggle_{rarity}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌐 Toggle Global Rarities for Character Spawning:", reply_markup=reply_markup)

async def toggle_rarity_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    rarity = query.data.replace("toggle_", "")
    settings = await global_settings.find_one({"_id": "rarity_config"}) or {"enabled_rarities": []}
    enabled = settings["enabled_rarities"]

    if rarity in enabled:
        enabled.remove(rarity)
    else:
        enabled.append(rarity)

    await global_settings.update_one(
        {"_id": "rarity_config"},
        {"$set": {"enabled_rarities": enabled}},
        upsert=True
    )

    # Refresh the menu
    keyboard = []
    for r in ALL_RARITIES:
        status = "✅" if r in enabled else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {r}", callback_data=f"toggle_{r}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🌐 Toggle Global Rarities for Character Spawning:", reply_markup=reply_markup)

# Register handlers
application.add_handler(CommandHandler("togglerarity", toggle_rarity_menu))
application.add_handler(CallbackQueryHandler(toggle_rarity_callback, pattern="^toggle_"))
