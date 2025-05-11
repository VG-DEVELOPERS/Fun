from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from shivu import shivuu as bot
from shivu import collection  # MongoDB anime collection

# Alphabet buttons
ALPHABETS = [chr(i) for i in range(65, 91)]  # A-Z


def get_letter_layout(page=0):
    chunk_size = 4  # 4 per row
    rows_per_page = 3
    buttons = []

    start = page * rows_per_page
    end = start + rows_per_page

    for i in range(start, end):
        if i * chunk_size >= len(ALPHABETS):
            break
        row = [
            InlineKeyboardButton(ALPHABETS[j], callback_data=f"anime_letter_{ALPHABETS[j]}")
            for j in range(i * chunk_size, min((i + 1) * chunk_size, len(ALPHABETS)))
        ]
        buttons.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"anime_page_{page - 1}"))
    if (end * chunk_size) < len(ALPHABETS):
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"anime_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    return buttons


@bot.on_message(filters.command("animelist"))
async def animelist_command(_, message: Message):
    text = "🔍 sᴇʟᴇᴄᴛ ᴀɴ sᴛᴀʀᴛɪɴɢ ʟᴇᴛᴛᴇʀ ᴏғ ᴀɴɪᴍᴇ ɴᴀᴍᴇ:"
    keyboard = InlineKeyboardMarkup(get_letter_layout(0))
    await message.reply_text(text, reply_markup=keyboard)


@bot.on_callback_query(filters.regex(r"anime_page_(\d+)"))
async def paginate_alphabets(_, query: CallbackQuery):
    page = int(query.matches[0].group(1))
    keyboard = InlineKeyboardMarkup(get_letter_layout(page))
    await query.message.edit_reply_markup(reply_markup=keyboard)


@bot.on_callback_query(filters.regex(r"anime_letter_([A-Z])"))
async def show_animes_by_letter(_, query: CallbackQuery):
    letter = query.matches[0].group(1)
    anime_cursor = collection.find({"anime": {"$regex": f"^{letter}", "$options": "i"}})
    anime_set = set()

    async for doc in anime_cursor:
        anime_set.add(doc["anime"])
    anime_list = sorted(list(anime_set))

    if not anime_list:
        return await query.answer("❎ No anime found for this letter.", show_alert=True)

    # First 3 only (page 0)
    anime_list = anime_list[:3]
    keyboard = [
        [InlineKeyboardButton(anime, callback_data=f"anime_select_{anime}")]
        for anime in anime_list
    ]
    keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"anime_next_{letter}_1")])

    await query.message.edit_text(
        f"🎌 Animes starting with **{letter}**:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@bot.on_callback_query(filters.regex(r"anime_next_([A-Z])_(\d+)"))
async def paginate_animes(_, query: CallbackQuery):
    letter = query.matches[0].group(1)
    page = int(query.matches[0].group(2))
    anime_cursor = collection.find({"anime": {"$regex": f"^{letter}", "$options": "i"}})
    anime_set = set()

    async for doc in anime_cursor:
        anime_set.add(doc["anime"])
    anime_list = sorted(list(anime_set))

    per_page = 3
    start = page * per_page
    end = start + per_page
    page_animes = anime_list[start:end]

    if not page_animes:
        return await query.answer("❎ No more animes!", show_alert=True)

    keyboard = [
        [InlineKeyboardButton(anime, callback_data=f"anime_select_{anime}")]
        for anime in page_animes
    ]

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"anime_next_{letter}_{page - 1}"))
    if end < len(anime_list):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"anime_next_{letter}_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    await query.message.edit_text(
        f"🎌 Animes starting with **{letter}**:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@bot.on_callback_query(filters.regex(r"anime_select_(.+)"))
async def selected_anime(_, query: CallbackQuery):
    anime = query.matches[0].group(1)
    text = (
        f'ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ **"{anime}"**\n'
        f'ᴘʟᴇᴀsᴇ ɢᴏ ɪɴʟɪɴᴇ ᴍᴏᴅᴇ ᴛᴏ sᴇᴇ ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴏғ ʏᴏᴜʀ ғᴀᴠᴏᴜʀɪᴛᴇ ᴀɴɪᴍᴇ'
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Go Inline", switch_inline_query_current_chat=anime)],
        [InlineKeyboardButton("🎯 Try in bot", url=f"https://t.me/Pick_Your_Waifu_Bot?start=inline")]
    ])
    await query.message.edit_text(text, reply_markup=keyboard)
  
