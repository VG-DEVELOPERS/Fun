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

# Caches
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

# Skin formatter
def format_character_name(name: str) -> str:
    skins = {
        "🏖️": "𝒃𝒆𝒂𝒄𝒉", "👘": "𝑲𝒊𝒎𝒐𝒏𝒐", "🧹": "𝑴𝒂𝒊𝒅", "🏀": "𝑩𝒂𝒔𝒌𝒆𝒕𝒃𝒂𝒍𝒍",
        "💍": "𝑩𝒓𝒊𝒅𝒆", "🏜️": "𝑨𝒓𝒂𝒃𝒊𝒂𝒏", "🗡️": "𝑺𝒘𝒐𝒓𝒅", "🦋": "𝑩𝒖𝒕𝒕𝒆𝒓𝒇𝒍𝒚",
        "🐉": "𝑫𝒓𝒂𝒈𝒐𝒏", "🐰": "𝑩𝒖𝒏𝒏𝒚", "🎒": "𝑺𝒄𝒉𝒐𝒐𝒍", "🌼": "𝑭𝒍𝒐𝒘𝒆𝒓𝒔"
    }
    for emoji, styled in skins.items():
        if emoji in name:
            base = name.split("-")[0]
            return f"{base}-[{emoji}{styled}{emoji}]"
    return name

# Main inline handler
async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset or 0)

    characters = []
    user_data = None

    # Use collection cache when no query
    if not query:
        characters = all_characters_cache.get('all_characters')
        if not characters:
            characters = await collection.find({}, {'_id': 0}).to_list(length=None)
            all_characters_cache['all_characters'] = characters

    elif query.startswith("collection."):
        user_id = query.split(" ")[0].split(".")[1]
        search_terms = " ".join(query.split(" ")[1:])
        user_data = user_collection_cache.get(user_id)

        if not user_data:
            user_data = await user_collection.find_one({'id': int(user_id)}, {'characters': 1})
            if user_data:
                user_collection_cache[user_id] = user_data

        if user_data:
            characters = list({c['id']: c for c in user_data.get('characters', [])}.values())
            if search_terms:
                regex = re.compile(search_terms, re.IGNORECASE)
                characters = [c for c in characters if regex.search(c['name']) or regex.search(c['anime'])]

    else:
        try:
            query_id = int(query)
            characters = await collection.find({'id': query_id}).to_list(length=50)
        except ValueError:
            regex = re.compile(re.escape(query), re.IGNORECASE)
            characters = await collection.find(
                {"$or": [{"name": regex}, {"anime": regex}]}
            ).to_list(length=50)

    results = []
    page = characters[offset:offset + 50]
    next_offset = str(offset + 50) if len(page) == 50 else ""

    for character in page:
        formatted_name = format_character_name(character['name'])

        if user_data:
            user_count = sum(c['id'] == character['id'] for c in user_data['characters'])
            owned_anime = sum(c['anime'] == character['anime'] for c in user_data['characters'])

            caption = (
                f"✨ <b>Character Unlocked!</b>\n\n"
                f"🍂 <b>Name:</b> {escape(formatted_name)}\n"
                f"🫧 <b>Series:</b> {escape(character['anime'])}\n"
                f"💥 <b>ID:</b> {character['id']} (x{user_count})\n"
                f"🔔 <b>Rarity:</b> {character['rarity']}\n"
                f"📦 <b>Your Anime Collection:</b> {owned_anime} / ?"
            )
        else:
            # REMOVE global count call (slow), or cache it externally if needed
            caption = (
                f"💸 <b>New Character Picked!</b>\n\n"
                f"🍂 <b>Name:</b> {escape(formatted_name)}\n"
                f"🫧 <b>Series:</b> {escape(character['anime'])}\n"
                f"💥 <b>ID:</b> {character['id']}\n"
                f"🔔 <b>Rarity:</b> {character['rarity']}"
            )

        results.append(
            InlineQueryResultPhoto(
                id=f"{character['id']}_{int(time.time() * 1000)}",
                photo_url=character['img_url'],
                thumbnail_url=character['img_url'],
                caption=caption,
                parse_mode='HTML'
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)
    
# Register handler
application.add_handler(InlineQueryHandler(inlinequery, block=False))
    
