import re
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

WRONG_FORMAT_TEXT = """Wrong ❌️ format...  eg. /upload Img_url muzan-kibutsuji Demon-slayer 3

img_url character-name anime-name rarity-number

use rarity number accordingly:

rarity_map = 
1 (⚪️ Common), 
2 (🟣 Rare), 
3 (🟡 Legendary), 
4 (🟢 Medium), 
5 (🔮 Limited edition), 
6 (⚜️ Premium), 
7 (🏖 Summer), 
8 (🎐 Crystal), 
9 (🫧 Mist), 
10 (❄️ Winter), 
11 (🍁 Autumn), 
12 (🌸 Festival)
13 (💞 Valentine)
"""

RARITY_MAP = {
    1: "⚪ Common",
    2: "🟣 Rare",
    3: "🟡 Legendary",
    4: "🟢 Medium",
    5: "🔮 Limited edition",
    6: "⚜️ Premium",
    7: "🏖 Summer",
    8: "🎐 Crystal",
    9: "🫧 Mist",
    10: "❄️ Winter",
    11: "🍁 Autumn",
    12: "🌸 Festival",
    13: "💞 Valentine"
}

def is_valid_url(url):
    regex = re.compile(
        r'^(https?://)'
        r'([\w\-]+\.)+[\w\-]{2,4}'
        r'(/[^\s]*)?$',
        re.IGNORECASE
    )
    return re.match(regex, url) is not None

async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']

# upload command 
async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Sensei...')
        return

    try:
        args = context.args
        if len(args) != 3 and len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        file_url = None
        file_type = None  # "photo" or "video"

        # Handle reply media
        if update.message.reply_to_message:
            reply = update.message.reply_to_message
            if reply.photo:
                file = reply.photo[-1]
                file_url = file.file_id
                file_type = "photo"
            elif reply.video:
                file = reply.video
                file_url = file.file_id
                file_type = "video"
            elif reply.document and reply.document.mime_type and reply.document.mime_type.startswith("video/"):
                file = reply.document
                file_url = file.file_id
                file_type = "video"
            else:
                await update.message.reply_text("Replied message must contain an image or a video (.mp4).")
                return
            offset = 0
        else:
            # Handle direct URL input
            file_url = args[0]
            if not is_valid_url(file_url):
                await update.message.reply_text('Invalid URL.')
                return
            file_type = "photo"
            offset = 1

        # Parse character info
        character_name = args[0 + offset].replace('-', ' ').title()
        anime = args[1 + offset].replace('-', ' ').title()
        try:
            rarity = RARITY_MAP[int(args[2 + offset])]
        except KeyError:
            await update.message.reply_text('Invalid rarity. Please use numbers from 1 to 13.')
            return

        # Generate unique ID
        char_id = str(await get_next_sequence_number('character_id')).zfill(2)

        # Create DB entry
        character = {
            'media_type': file_type,
            'file_id': file_url,
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': char_id
        }

        # Send to channel
        caption = (
            f'<b>Character Name:</b> {character_name}\n'
            f'<b>Anime Name:</b> {anime}\n'
            f'<b>Rarity:</b> {rarity}\n'
            f'<b>ID:</b> {char_id}\n'
            f'Added by <a href="tg://user?id={update.effective_user.id}">'
            f'{update.effective_user.first_name}</a>'
        )

        try:
            if file_type == "photo":
                msg = await context.bot.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=file_url,
                    caption=caption,
                    parse_mode='HTML'
                )
            else:  # video
                msg = await context.bot.send_video(
                    chat_id=CHARA_CHANNEL_ID,
                    video=file_url,
                    caption=caption,
                    parse_mode='HTML'
                )

            character['message_id'] = msg.message_id
            await collection.insert_one(character)
            await update.message.reply_text('Character added successfully.')

        except Exception:
            await collection.insert_one(character)
            await update.message.reply_text("Character added, but failed to send to channel.")

    except Exception as e:
        await update.message.reply_text(f'Upload failed. Error: {str(e)}\nContact support: {SUPPORT_CHAT}')
        

# /delete command
async def delete(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask my Sensei to use this command.')
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format. Use: /delete ID')
            return

        character = await collection.find_one_and_delete({'id': args[0]})
        if character:
            try:
                await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
                await update.message.reply_text('Character deleted successfully.')
            except:
                await update.message.reply_text('Character deleted from DB, but not found in channel.')
        else:
            await update.message.reply_text('Character not found in database.')
    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')

# /update command
async def update_char(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text('Incorrect format. Use: /update id field new_value')
            return

        char_id, field, value = args
        character = await collection.find_one({'id': char_id})
        if not character:
            await update.message.reply_text('Character not found.')
            return

        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if field not in valid_fields:
            await update.message.reply_text(f'Invalid field. Choose from: {", ".join(valid_fields)}')
            return

        if field == 'name' or field == 'anime':
            new_value = value.replace('-', ' ').title()
        elif field == 'rarity':
            try:
                new_value = RARITY_MAP[int(value)]
            except KeyError:
                await update.message.reply_text('Invalid rarity number. Use 1–13.')
                return
        elif field == 'img_url':
            if not is_valid_url(value):
                await update.message.reply_text('Invalid image URL.')
                return
            new_value = value
        else:
            new_value = value

        await collection.find_one_and_update({'id': char_id}, {'$set': {field: new_value}})

        # Update channel message
        updated_character = await collection.find_one({'id': char_id})

        try:
            if field == 'img_url':
                await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
                message = await context.bot.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=new_value,
                    caption=f"<b>Character Name:</b> {updated_character['name']}\n<b>Anime Name:</b> {updated_character['anime']}\n<b>Rarity:</b> {updated_character['rarity']}\n<b>ID:</b> {updated_character['id']}\nUpdated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                    parse_mode='HTML'
                )
                await collection.find_one_and_update({'id': char_id}, {'$set': {'message_id': message.message_id}})
            else:
                await context.bot.edit_message_caption(
                    chat_id=CHARA_CHANNEL_ID,
                    message_id=character['message_id'],
                    caption=f"<b>Character Name:</b> {updated_character['name']}\n<b>Anime Name:</b> {updated_character['anime']}\n<b>Rarity:</b> {updated_character['rarity']}\n<b>ID:</b> {updated_character['id']}\nUpdated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                    parse_mode='HTML'
                )
        except Exception:
            await update.message.reply_text("Field updated in DB, but failed to update channel message.")

        await update.message.reply_text('Character updated successfully.')
    except Exception as e:
        await update.message.reply_text(f'Update failed. Error: {str(e)}')

# Register command handlers
UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
DELETE_HANDLER = CommandHandler('delete', delete, block=False)
UPDATE_HANDLER = CommandHandler('update', update_char, block=False)

application.add_handler(UPLOAD_HANDLER)
application.add_handler(DELETE_HANDLER)
application.add_handler(UPDATE_HANDLER)
        
