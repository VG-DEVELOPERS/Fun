import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import ASCENDING

from telegram import Update, InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler, CallbackContext

from shivu import user_collection, collection, application

# MongoDB indexes
collection.create_index([('id', ASCENDING)])
collection.create_index([('anime', ASCENDING)])
collection.create_index([('img_url', ASCENDING)])
user_collection.create_index([('characters.id', ASCENDING)])

# Caching
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)


async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    # Check if it's a user collection lookup
    if query.startswith("collection."):
        user_id, *search_terms = query.split(" ")[0].split(".")[1], " ".join(query.split(" ")[1:])
        user_data = user_collection_cache.get(user_id)

        if not user_data:
            user_data = await user_collection.find_one({'id': int(user_id)})
            user_collection_cache[user_id] = user_data

        if not user_data:
            characters = []
        else:
            characters = list({c['id']: c for c in user_data.get('characters', [])}.values())
            if search_terms:
                regex = re.compile(search_terms, re.IGNORECASE)
                characters = [c for c in characters if regex.search(c['name']) or regex.search(c['anime'])]

    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            characters = await collection.find({"$or": [{"name": regex}, {"anime": regex}]}).to_list(length=None)
        else:
            characters = all_characters_cache.get('all_characters')
            if not characters:
                characters = await collection.find({}).to_list(length=None)
                all_characters_cache['all_characters'] = characters

    results = []
    page = characters[offset:offset + 50]
    next_offset = str(offset + 50) if len(page) == 50 else ""

    for character in page:
        if query.startswith("collection."):
            user_count = sum(c['id'] == character['id'] for c in user_data['characters'])
            total_anime = await collection.count_documents({'anime': character['anime']})
            owned_anime = sum(c['anime'] == character['anime'] for c in user_data['characters'])
            caption = (
                f"✨ <b>Character Unlocked!</b>\n\n"
                f"🌍 <b>Series:</b> {escape(character['anime'])}\n"
                f"🎴 <b>ID:</b> {character['id']} — {escape(character['name'])} (x{user_count})\n\n"
                f"🏆 <b>Rarity:</b> {character['rarity']}\n"
                f"📦 <b>Your Anime Collection:</b> {owned_anime}/{total_anime}"
            )
        else:
            global_count = await user_collection.count_documents({'characters.id': character['id']})
            caption = (
                f"✨ <b>Character Unlocked!</b>\n\n"
                f"🌍 <b>Series:</b> {escape(character['anime'])}\n"
                f"🎴 <b>ID:</b> {character['id']} — {escape(character['name'])}\n\n"
                f"🏆 <b>Rarity:</b> {character['rarity']}\n"
                f"🔁 <b>Globally caught {global_count} times...</b>"
            )

        results.append(
            InlineQueryResultPhoto(
                id=f"{character['id']}_{time.time()}",
                photo_url=character['img_url'],
                thumbnail_url=character['img_url'],
                caption=caption,
                parse_mode='HTML'
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)


# Handler registration
application.add_handler(InlineQueryHandler(inlinequery, block=False))
