import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from functools import wraps
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from shivu import (
    collection, top_global_groups_collection, group_user_totals_collection,
    user_collection, user_totals_collection, shivuu, application, LOGGER, gban_collection
)
from shivu.modules import ALL_MODULES

# Dynamically import all modules
for module_name in ALL_MODULES:
    importlib.import_module("shivu.modules." + module_name)
    

locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
last_user = {}
warned_users = {}

# Define spawn rarity thresholds
RARITY_THRESHOLDS = {
    "⚪ Common": 100,
    "🟢 Medium": 200,
    "🟣 Rare": 300,
    "🟡 Legendary": 500,
    "🔮 limited edition": 800,
    "⚜️ premium": 1500,
    "🎐 Crystal": 2500,
    "🎊 Festival": 180000000,
    "❄️ Winter": 2000000000,
    "🌞 Summer": 2000000000,
    "🍁 Autumn": 2000000000,
    "🌫️ Mist": 2000
}



def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 100) if chat_frequency else 100

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(f"⚠️ Don't Spam {update.effective_user.first_name}...")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        if message_counts[chat_id] >= message_frequency:
            message_counts[chat_id] = 0
            await send_image(update, context)

async def sendimage(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    available_characters = [c for c in all_characters if c['id'] not in sent_characters[chat_id]]
    if not available_characters:
        sent_characters[chat_id] = []
        available_characters = all_characters

    character = random.choice(available_characters)

    # Check rarity threshold
    required_messages = RARITY_THRESHOLDS.get(character["rarity"], 100)
    if message_counts.get(chat_id, 0) < required_messages:
        return  # Don't send if rarity threshold not met

    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    first_correct_guesses.pop(chat_id, None)

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Already Guessed By Someone.. Try Next Time.")
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    if any(x in guess for x in ['()', '&']):
        await update.message.reply_text("❌ Invalid characters in guess.")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id

        user = await user_collection.find_one({'id': user_id})
        if user:
            update_fields = {}
            if update.effective_user.username != user.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [last_characters[chat_id]],
            })

        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {'$inc': {'count': 1}},
            upsert=True
        )

        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {'$inc': {'count': 1}, '$set': {'group_name': update.effective_chat.title}},
            upsert=True
        )

        keyboard = [[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You Guessed a New Character ✅\n\n'
            f'<b>NAME:</b> {last_characters[chat_id]["name"]}\n<b>ANIME:</b> {last_characters[chat_id]["anime"]}\n<b>RARITY:</b> {last_characters[chat_id]["rarity"]}',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Please write correct character name.")

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text('Please provide character ID.')
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('You have no guessed characters yet.')
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('This character is not in your collection.')
        return

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})
    await update.message.reply_text(f'Character {character["name"]} has been added to your favorites.')

def main() -> None:
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()
                
