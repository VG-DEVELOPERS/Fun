import os
import random
import html

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import (
    application, PHOTO_URL, OWNER_ID,
    user_collection, top_global_groups_collection,
    group_user_totals_collection, sudo_users as SUDO_USERS
)


# Top menu with buttons
async def top_menu(update: Update, context: CallbackContext) -> None:
    buttons = [
        [InlineKeyboardButton("📊 Top Users", callback_data="top_users")],
        [InlineKeyboardButton("👥 Top Groups", callback_data="top_groups")],
        [InlineKeyboardButton("🏆 Group Collectors", callback_data="group_collectors")]
    ]
    photo_url = random.choice(PHOTO_URL)
    await update.message.reply_photo(
        photo=photo_url,
        caption="📈 Choose a leaderboard to view:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# Callback for button presses
async def leaderboard_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "top_users":
        cursor = user_collection.aggregate([
            {"$project": {"username": 1, "first_name": 1, "character_count": {"$size": "$characters"}}},
            {"$sort": {"character_count": -1}}, {"$limit": 10}
        ])
        leaderboard_data = await cursor.to_list(length=10)
        title = "<b>🏅 TOP 10 USERS WITH MOST CHARACTERS</b>\n\n"

    elif data == "top_groups":
        cursor = top_global_groups_collection.aggregate([
            {"$project": {"group_name": 1, "count": 1}},
            {"$sort": {"count": -1}}, {"$limit": 10}
        ])
        leaderboard_data = await cursor.to_list(length=10)
        title = "<b>👑 TOP 10 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"

    elif data == "group_collectors":
        chat_id = query.message.chat.id
        cursor = group_user_totals_collection.aggregate([
            {"$match": {"group_id": chat_id}},
            {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
            {"$sort": {"character_count": -1}}, {"$limit": 10}
        ])
        leaderboard_data = await cursor.to_list(length=10)
        title = "<b>🏆 TOP 10 USERS IN THIS GROUP</b>\n\n"

    else:
        return

    leaderboard_message = title
    for i, entry in enumerate(leaderboard_data, start=1):
        if "group_name" in entry:
            name = html.escape(entry.get('group_name', 'Unknown'))[:15] + "..."
            count = entry['count']
            leaderboard_message += f"{i}. <b>{name}</b> ➾ <b>{count}</b>\n"
        else:
            username = entry.get("username", "unknown")
            name = html.escape(entry.get("first_name", "unknown"))[:15] + "..."
            count = entry.get("character_count", 0)
            leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{name}</b></a> ➾ <b>{count}</b>\n'

    # Reuse the same photo and update the caption
    await query.edit_message_caption(
        caption=leaderboard_message,
        parse_mode="HTML",
        reply_markup=query.message.reply_markup
    )


# Command for bot stats (OWNER only)
async def stats(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    user_count = await user_collection.count_documents({})
    group_count = await group_user_totals_collection.distinct("group_id")
    await update.message.reply_text(f"Total Users: {user_count}\nTotal Groups: {len(group_count)}")


# SUDO: Export user list
async def send_users_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        return await update.message.reply_text('Only for Sudo users...')
    users = await user_collection.find({}).to_list(length=None)
    with open('users.txt', 'w') as f:
        for user in users:
            f.write(f"{user.get('first_name', 'Unknown')}\n")
    with open('users.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
    os.remove('users.txt')


# SUDO: Export group list
async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        return await update.message.reply_text('Only for Sudo users...')
    groups = await top_global_groups_collection.find({}).to_list(length=None)
    with open('groups.txt', 'w') as f:
        for group in groups:
            f.write(f"{group.get('group_name', 'Unknown')}\n")
    with open('groups.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
    os.remove('groups.txt')


# Register all handlers
application.add_handler(CommandHandler("top", top_menu, block=False))
application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^(top_users|top_groups|group_collectors)$"))
application.add_handler(CommandHandler("stats", stats, block=False))
application.add_handler(CommandHandler("list", send_users_document, block=False))
application.add_handler(CommandHandler("groups", send_groups_document, block=False))
                       
