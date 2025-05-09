import random
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import pm_users as collection


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    user_data = await collection.find_one({"_id": user_id})

    if user_data is None:
        await collection.insert_one({
            "_id": user_id,
            "first_name": first_name,
            "username": username
        })

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🎉 New user started the bot!\n👤 User: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>",
            parse_mode='HTML'
        )
    else:
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await collection.update_one(
                {"_id": user_id},
                {"$set": {"first_name": first_name, "username": username}}
            )

    photo_url = random.choice(PHOTO_URL)

    keyboard = [
        [InlineKeyboardButton("➕ Add Me", url=f'http://t.me/{BOT_USERNAME}?startgroup=new')],
        [
            InlineKeyboardButton("🛠 Support", url=f'https://t.me/{SUPPORT_CHAT}'),
            InlineKeyboardButton("📢 Updates", url=f'https://t.me/{UPDATE_CHAT}')
        ],
        [InlineKeyboardButton("📖 Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.effective_chat.type == "private":
       caption = f"""
👋 **Welcome, {escape(first_name)}!**

🎌 I am **Waifu Warzone** — your gateway to anime glory!  
I randomly **summon anime characters** in your groups.  
Your mission? **Guess them**, **collect them**, and **build your dream roster** of waifus and husbandos!

🔥 Compete with friends and climb the leaderboard  
🎮 Unlock rare and legendary characters  
🤝 Trade, gift, and flex your ultimate collection!

🚀 Ready to rise as the true waifu master?  
Tap **Help** to learn the ropes or click **Add Me** to bring the magic to your group!

🌸 Let the waifu wars begin!
"""

    else:
        caption = "🎴 I'm alive! Start a private chat with me for full waifu collecting action!"

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo_url,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode='markdown'
    )


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_text = """
🛠️ **Help Menu** 🛠️

🎯 /guess — Try to guess the character (group only)  
❤️ /fav — Add a character to your favorites  
🔁 /trade — Trade characters with others  
🎁 /gift — Gift a character to another user (group only)  
📦 /collection — View your personal collection  
🏆 /top — View the top users leaderboard  
🏅 /topgroups — Top active guessing groups  
📊 /ctop — Your personal stats  
⏰ /changetime — Set spawn time (group only)
        """

        help_keyboard = [[InlineKeyboardButton("⤾ Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(help_keyboard)

        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=help_text,
            reply_markup=reply_markup,
            parse_mode='markdown'
        )

    elif query.data == 'back':
        caption = f"""
🌟 **Welcome Back, Senpai!**  

I'm **Waifu Warzone** — your personal anime summoner!  
Step into a world where waifus appear from thin air,  
and only the fastest, smartest, and luckiest can claim them!

✨ Unlock your dream collection  
⚔️ Battle friends in guess-offs  
🎁 Gift, trade & dominate the leaderboard!

Ready to summon your destiny?  
Tap **Add Me** to begin your legend, or hit **Help** to master the commands!
"""

        keyboard = [
            [InlineKeyboardButton("➕ Add Me", url=f'http://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton("🛠 Support", url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton("📢 Updates", url=f'https://t.me/{UPDATE_CHAT}')
            ],
            [InlineKeyboardButton("📖 Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='markdown'
        )


# Register handlers
application.add_handler(CallbackQueryHandler(button, pattern='^help$|^back$', block=False))
start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)
