import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from shivu import (
    collection,
    top_global_groups_collection,
    group_user_totals_collection,
    user_collection,
    user_totals_collection,
    application,
    db,
    LOGGER,
    shivuu
)

# MongoDB config collection for enabled rarities per chat
group_config_collection = db["group_config"]

# Rarity spawn thresholds
RARITY_THRESHOLDS = {
    "⚪ Common": 100,
    "🟢 Medium": 200,
    "🟣 Rare": 300,
    "🟡 Legendary": 500,
    "🔮 Limited edition": 800,
    "⚜️ Premium": 1500,
    "🎐 Crystal": 2500,
    "🏖 Summer": 2000,
    "❄️ Winter": 2000,
    "🍁 Autumn": 2000,
    "🫧 Mist": 2000,
    "🌸 Festival": 1800
}

locks = {}
message_counts = {}
sent_characters = {}
last_characters = {}
first_correct_guesses = {}
last_user = {}
warned_users = {}

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def get_enabled_rarities(chat_id):
    config = await group_config_collection.find_one({'chat_id': chat_id})
    return config.get('enabled_rarities', list(RARITY_THRESHOLDS.keys())) if config else list(RARITY_THRESHOLDS.keys())

async def toggle_rarity(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /toggle_rarity <rarity> <on/off>")
        return

    rarity_input = ' '.join(context.args[:-1]).strip().capitalize()
    status = context.args[-1].lower()
    chat_id = update.effective_chat.id

    matching = [r for r in RARITY_THRESHOLDS if rarity_input.lower() in r.lower()]
    if not matching:
        await update.message.reply_text("Rarity not found.")
        return

    rarity = matching[0]
    config = await group_config_collection.find_one({'chat_id': chat_id}) or {}
    enabled = set(config.get("enabled_rarities", list(RARITY_THRESHOLDS.keys())))

    if status == "on":
        enabled.add(rarity)
    elif status == "off":
        enabled.discard(rarity)
    else:
        await update.message.reply_text("Specify 'on' or 'off'")
        return

    await group_config_collection.update_one(
        {'chat_id': chat_id},
        {'$set': {'enabled_rarities': list(enabled)}},
        upsert=True
    )
    await update.message.reply_text(f"Rarity '{rarity}' is now {'enabled' if status == 'on' else 'disabled'}.")

async def send_image(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    all_characters = await collection.find({}).to_list(length=None)
    enabled_rarities = await get_enabled_rarities(chat_id)
    message_count = message_counts.get(chat_id, 0)

    valid_characters = [
        char for char in all_characters
        if char['rarity'] in enabled_rarities and message_count % RARITY_THRESHOLDS[char['rarity']] == 0
    ]

    if not valid_characters:
        return

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    pool = [c for c in valid_characters if c['id'] not in sent_characters[chat_id]]
    if not pool:
        sent_characters[chat_id] = []
        pool = valid_characters

    character = random.choice(pool)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A New {character['rarity']} Character Appeared...\n/guess Character Name to catch!",
        parse_mode='Markdown'
    )

async def message_counter(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()

    async with locks[chat_id]:
        chat_data = await user_totals_collection.find_one({'chat_id': chat_id}) or {}
        message_frequency = chat_data.get('message_frequency', 100)

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text("⚠️ Stop spamming... You'll be ignored for 10 mins.")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        await send_image(update, context)

async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Already guessed. Try next time.")
        return

    guess = ' '.join(context.args).lower()
    if "()" in guess or "&" in guess:
        await update.message.reply_text("Invalid characters in guess.")
        return

    target = last_characters[chat_id]
    name_parts = target['name'].lower().split()

    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        user = await user_collection.find_one({'id': user_id})
        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': target}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [target],
            })

        await update.message.reply_text(
            f"<b>{escape(update.effective_user.first_name)}</b> guessed correctly!\n"
            f"Name: <b>{target['name']}</b>\nAnime: <b>{target['anime']}</b>\nRarity: <b>{target['rarity']}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]])
        )
    else:
        await update.message.reply_text("Incorrect name. Try again.")
        
async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    
    if not context.args:
        await update.message.reply_text('Please provide Character id...')
        return

    character_id = context.args[0]

    
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('You have not Guessed any characters yet....')
        return


    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('This Character is Not In your collection')
        return

    
    user['favorites'] = [character_id]

    
    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': user['favorites']}})

    await update.message.reply_text(f'Character {character["name"]} has been added to your favorite...')
    


def main():
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(CommandHandler("setrarity", toggle_rarity, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()
    
