import re
import time
from html import escape
from uuid import uuid4
from cachetools import TTLCache
from pymongo import ASCENDING

from telegram import InlineQueryResultPhoto, Update
from telegram.ext import InlineQueryHandler, CallbackContext

from shivu import user_collection, collection, application, db

# Indexing for performance
db.characters.create_index([('id', ASCENDING)])
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])
db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])

# Caching
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def inlinequery(update: Update, context: CallbackContext):
    query = update.inline_query.query.strip()
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0
    results = []

    characters = []
    user = None

    if query.startswith('collection.'):
        parts = query.split(' ')
        user_part = parts[0].split('.')
        search_terms = ' '.join(parts[1:]) if len(parts) > 1 else ""

        if len(user_part) > 1 and user_part[1].isdigit():
            user_id = int(user_part[1])

            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await user_collection.find_one({'id': user_id})
                user_collection_cache[user_id] = user

            if user:
                characters = list({c['id']: c for c in user.get('characters', [])}.values())
                if search_terms:
                    regex = re.compile(search_terms, re.IGNORECASE)
                    characters = [c for c in characters if regex.search(c['name']) or regex.search(c['anime'])]
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            characters = await collection.find({
                "$or": [{"name": regex}, {"anime": regex}]
            }).to_list(length=1000)
        else:
            characters = all_characters_cache.get('all_characters')
            if not characters:
                characters = await collection.find({}).to_list(length=1000)
                all_characters_cache['all_characters'] = characters

    total = len(characters)
    characters = characters[offset:offset + 50]
    next_offset = str(offset + 50) if offset + 50 < total else ""

    for character in characters:
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        anime_total = await collection.count_documents({'anime': character['anime']})

        if user:
            user_char_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_count = sum(c['anime'] == character['anime'] for c in user['characters'])
            caption = (
                f"<b>🌟 Collection of <a href='tg://user?id={user['id']}'>{escape(user.get('first_name', str(user['id'])))}</a></b>\n\n"
                f"🎴 <b>{character['name']}</b> (x{user_char_count})\n"
                f"🌸 <b>{character['anime']}</b> ({user_anime_count}/{anime_total})\n"
                f"🏅 <b>{character.get('rarity', 'Unknown')}</b>\n"
                f"🆔️ <code>{character['id']}</code>"
            )
        else:
            caption = (
                f"<b>✨ Character Spotlight</b>\n\n"
                f"🎴 <b>{character['name']}</b>\n"
                f"🌸 <b>{character['anime']}</b>\n"
                f"🏅 <b>{character.get('rarity', 'Unknown')}</b>\n"
                f"🆔️ <code>{character['id']}</code>\n"
                f"🌍 Guessed Globally: <b>{global_count}</b> times"
            )

        results.append(
            InlineQueryResultPhoto(
                id=str(uuid4()),
                photo_url=character['img_url'],
                thumbnail_url=character['img_url'],
                caption=caption,
                parse_mode='HTML'
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

# Register handler
application.add_handler(InlineQueryHandler(inlinequery, block=False))
