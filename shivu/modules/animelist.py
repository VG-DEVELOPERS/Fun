from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from shivu import shivuu as bot
from shivu import collection

# Alphabet chunks for layout
ALPHABETS = ["A", "B", "C", "D", "E", "F", "G", "H",
             "I", "J", "K", "L", "M", "N", "O", "P",
             "Q", "R", "S", "T", "U", "V", "W", "X",
             "Y", "Z"]

def get_letter_layout(page=0):
    chunk_size = 4
    buttons = []
    start = page * 3
    end = start + 3
    for i in range(start, end):
        if i >= len(ALPHABETS):
            break
        row = [InlineKeyboardButton(ALPHABETS[j], callback_data=f"anime_letter_{ALPHABETS[j]}")
               for j in range(i * chunk_size, min((i + 1) * chunk_size, len(ALPHABETS)))]
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
    anime_list = sorted(set())
    async for doc in anime_cursor:
        anime_list.add(doc["anime"])
    anime_list = sorted(list(anime_list))

    if not anime_list:
        return await query.answer("No anime found for this letter.", show_alert=True)

    anime_list = anime_list[:3]  # First 3 for now
    keyboard = [
        [InlineKeyboardButton(anime, callback_data=f"anime_select_{anime}")]
        for anime in anime_list
    ]
    keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"anime_next_{letter}_1")])
    await query.message.edit_text(f"🎌 Animes starting with **{letter}**:", reply_markup=InlineKeyboardMarkup(keyboard))

@bot.on_callback_query(filters.regex(r"anime_next_([A-Z])_(\d+)"))
async def paginate_animes(_, query: CallbackQuery):
    letter = query.matches[0].group(1)
    page = int(query.matches[0].group(2))
    anime_cursor = collection.find({"anime": {"$regex": f"^{letter}", "$options": "i"}})
    anime_list = sorted(set())
    async for doc in anime_cursor:
        anime_list.add(doc["anime"])
    anime_list = sorted(list(anime_list))

    per_page = 3
    start = page * per_page
    end = start + per_page
    page_animes = anime_list[start:end]
    if not page_animes:
        return await query.answer("No more animes!", show_alert=True)

    keyboard = [
        [InlineKeyboardButton(anime, callback_data=f"anime_select_{anime}")]
        for anime in page_animes
    ]
    if start > 0:
        keyboard.append([
            InlineKeyboardButton("⬅️ Previous", callback_data=f"anime_next_{letter}_{page-1}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"anime_next_{letter}_{page+1}")
        ])
    else:
        keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"anime_next_{letter}_{page+1}")])
    await query.message.edit_text(f"🎌 Animes starting with **{letter}**:", reply_markup=InlineKeyboardMarkup(keyboard))

@bot.on_callback_query(filters.regex(r"anime_select_(.+)"))
async def selected_anime(_, query: CallbackQuery):
    anime = query.matches[0].group(1)
    text = f'ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ **"{anime}"**\nᴘʟᴇᴀsᴇ ɢᴏ ɪɴʟɪɴᴇ ᴍᴏᴅᴇ ᴛᴏ sᴇᴇ ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴏғ ʏᴏᴜʀ ғᴀᴠᴏᴜʀɪᴛᴇ ᴀɴɪᴍᴇ'
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Go Inline", switch_inline_query_current_chat=anime)]
    ])
    await query.message.edit_text(text, reply_markup=keyboard)
      
