import os
import random
import html

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import (
    application, PHOTO_URL, OWNER_ID,
    user_collection, top_global_groups_collection,
    group_user_totals_collection, sudo_users as SUDO_USERS
)


# Helper: create the buttons
def get_leaderboard_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏅 Top Users", callback_data="top_users")],
        [InlineKeyboardButton("👥 Top Groups", callback_data="top_groups")],
        [InlineKeyboardButton("🏆 Group Collectors", callback_data="group_collectors")]
    ])


# Shared function to build and return leaderboard messages
async def build_leaderboard_text(data_type, chat_id=None):
    if data_type == "top_users":
        cursor = user_collection.aggregate([
            {"$project": {"username": 1, "first_name": 1, "character_count": {"$size": "$characters"}}},
            {"$sort": {"character_count": -1}}, {"$limit": 10}
        ])
        title = "🏅 <b>TOP 10 USERS WITH MOST CHARACTERS</b>"
    elif data_type == "top_groups":
        cursor = top_global_groups_collection.aggregate([
            {"$project": {"group_name": 1, "count": 1}},
            {"$sort": {"count": -1}}, {"$limit": 10}
        ])
        title = "👥 <b>TOP 10 GROUPS WHO GUESSED MOST CHARACTERS</b>"
    elif data_type == "group_collectors":
        cursor = group_user_totals_collection.aggregate([
            {"$match": {"group_id": chat_id}},
            {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
            {"$sort": {"character_count": -1}}, {"$limit": 10}
        ])
        title = "🏆 <b>TOP 10 USERS IN THIS GROUP</b>"
    else:
        return None

    data = await cursor.to_list(length=10)
    lines = [f"{title}\n━━━━━━━━━━━━━━━━━━━━━━"]

    for i, item in enumerate(data, 1):
        if "group_name" in item:
            name = html.escape(item.get("group_name", "Unknown"))[:15] + "..."
            count = item["count"]
            lines.append(f"✨ <b>{i}. {name}</b> — <code>{count}</code>")
        else:
            username = item.get("username", "unknown")
            name = html.escape(item.get("first_name", "unknown"))[:15] + "..."
            count = item.get("character_count", 0)
            lines.append(f"✨ <b>{i}. <a href='https://t.me/{username}'>{name}</a></b> — <code>{count}</code>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# /top command: default is top users
async def top_menu(update: Update, context: CallbackContext) -> None:
    photo_url = random.choice(PHOTO_URL)
    leaderboard_text = await build_leaderboard_text("top_users")
    await update.message.reply_photo(
        photo=photo_url,
        caption=leaderboard_text,
        parse_mode="HTML",
        reply_markup=get_leaderboard_buttons()
    )


# Button press handler
async def leaderboard_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data_type = query.data
    chat_id = query.message.chat.id
    leaderboard_text = await build_leaderboard_text(data_type, chat_id)
    await query.edit_message_caption(
        caption=leaderboard_text,
        parse_mode="HTML",
        reply_markup=get_leaderboard_buttons()
    )


# OWNER: Basic bot stats
async def stats(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You're not authorized.")
        return
    user_count = await user_collection.count_documents({})
    group_count = await group_user_totals_collection.distinct("group_id")
    await update.message.reply_text(f"📊 Total Users: {user_count}\n👥 Total Groups: {len(group_count)}")


# SUDO: Export users
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


# SUDO: Export groups
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


# Register handlers
application.add_handler(CommandHandler("top", top_menu, block=False))
application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^(top_users|top_groups|group_collectors)$"))
application.add_handler(CommandHandler("stats", stats, block=False))
application.add_handler(CommandHandler("list", send_users_document, block=False))
application.add_handler(CommandHandler("groups", send_groups_document, block=False))
