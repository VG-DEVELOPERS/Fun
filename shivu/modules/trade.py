from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from shivu import user_collection, shivuu

pending_trades = {}


@shivuu.on_message(filters.command("trade"))
async def trade(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to trade a character!")
        return

    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        await message.reply_text("You can't trade a character with yourself!")
        return

    if len(message.command) != 3:
        await message.reply_text("You need to provide two character IDs!")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    sender_character = next((character for character in sender['characters'] if character['id'] == sender_character_id), None)
    receiver_character = next((character for character in receiver['characters'] if character['id'] == receiver_character_id), None)

    if not sender_character:
        await message.reply_text("You don't have the character you're trying to trade!")
        return

    if not receiver_character:
        await message.reply_text("The other user doesn't have the character they're trying to trade!")
        return






    if len(message.command) != 3:
        await message.reply_text("/trade [Your Character ID] [Other User Character ID]!")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    
    pending_trades[(sender_id, receiver_id)] = (sender_character_id, receiver_character_id)

    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm Trade", callback_data="confirm_trade")],
            [InlineKeyboardButton("Cancel Trade", callback_data="cancel_trade")]
        ]
    )

    await message.reply_text(f"{message.reply_to_message.from_user.mention}, do you accept this trade?", reply_markup=keyboard)


@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data in ["confirm_trade", "cancel_trade"]))
async def on_callback_query(client, callback_query):
    receiver_id = callback_query.from_user.id

    
    for (sender_id, _receiver_id), (sender_character_id, receiver_character_id) in pending_trades.items():
        if _receiver_id == receiver_id:
            break
    else:
        await callback_query.answer("This is not for you!", show_alert=True)
        return

    if callback_query.data == "confirm_trade":
        
        sender = await user_collection.find_one({'id': sender_id})
        receiver = await user_collection.find_one({'id': receiver_id})

        sender_character = next((character for character in sender['characters'] if character['id'] == sender_character_id), None)
        receiver_character = next((character for character in receiver['characters'] if character['id'] == receiver_character_id), None)

        
        
        sender['characters'].remove(sender_character)
        receiver['characters'].remove(receiver_character)

        
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
        await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

        
        sender['characters'].append(receiver_character)
        receiver['characters'].append(sender_character)

        
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
        await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

        
        del pending_trades[(sender_id, receiver_id)]

        await callback_query.message.edit_text(f"You have successfully traded your character with {callback_query.message.reply_to_message.from_user.mention}!")

    elif callback_query.data == "cancel_trade":
        
        del pending_trades[(sender_id, receiver_id)]

        await callback_query.message.edit_text("❌️ Sad Cancelled....")





pending_gifts = {}

@shivuu.on_message(filters.command("gift"))
async def gift_character(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        return await message.reply_text("🎁 Reply to the user you want to gift a character to!")

    receiver = message.reply_to_message.from_user
    receiver_id = receiver.id

    if sender_id == receiver_id:
        return await message.reply_text("😅 You can't gift a character to yourself!")

    if len(message.command) != 2:
        return await message.reply_text("Usage:\n`/gift <character_id>`", parse_mode="Markdown")

    character_id = message.command[1]
    sender = await user_collection.find_one({'id': sender_id})

    if not sender or 'characters' not in sender:
        return await message.reply_text("❌ You have no characters to gift.")

    # Find the character in sender's list
    character_list = sender['characters']
    character_index = next((i for i, char in enumerate(character_list) if char['id'] == character_id), None)

    if character_index is None:
        return await message.reply_text("❌ You don't own this character.")

    character = character_list[character_index]

    # Store gift pending
    pending_gifts[(sender_id, receiver_id)] = {
        'character': character,
        'index': character_index,
        'receiver_first_name': receiver.first_name,
        'receiver_username': receiver.username,
    }

    # Buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Gift", callback_data="confirm_gift")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_gift")]
    ])

    await message.reply_text(
        f"🎁 Do you really want to gift character **{character['name']}** to [{receiver.first_name}](tg://user?id={receiver_id})?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data in ["confirm_gift", "cancel_gift"]))
async def handle_gift_confirm(client, callback_query):
    sender_id = callback_query.from_user.id

    for (s_id, r_id), gift_data in pending_gifts.items():
        if s_id == sender_id:
            break
    else:
        return await callback_query.answer("This gift request is not for you.", show_alert=True)

    receiver_id = r_id
    gift_character = gift_data['character']

    if callback_query.data == "confirm_gift":
        sender = await user_collection.find_one({'id': sender_id})
        receiver = await user_collection.find_one({'id': receiver_id})

        # Remove 1 copy only
        sender['characters'].pop(gift_data['index'])
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})

        # Add to receiver
        if receiver:
            existing_ids = [c['id'] for c in receiver.get('characters', [])]
            if gift_character['id'] not in existing_ids:
                await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': gift_character}})
        else:
            await user_collection.insert_one({
                'id': receiver_id,
                'username': gift_data['receiver_username'],
                'first_name': gift_data['receiver_first_name'],
                'characters': [gift_character]
            })

        # Cleanup
        del pending_gifts[(sender_id, receiver_id)]

        await callback_query.message.edit_text(
            f"🎁 You have successfully gifted **{gift_character['name']}** to [{gift_data['receiver_first_name']}](tg://user?id={receiver_id})!",
            parse_mode="Markdown"
        )

    elif callback_query.data == "cancel_gift":
        del pending_gifts[(sender_id, receiver_id)]
        await callback_query.message.edit_text("❌ Gift cancelled.")

