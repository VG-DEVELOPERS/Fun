from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import CallbackContext
from shivu import collection, application # Make sure this points to your character collection

async def total_characters(update: Update, context: CallbackContext) -> None:
    try:
        total = await collection.count_documents({})
        await update.message.reply_text(f"📦 Total characters in database: {total}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching total: {str(e)}")

application.add_handler(CommandHandler("total", total_characters, block=False))
