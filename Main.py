import json
import os
import uuid
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters, CallbackQueryHandler,
    ContextTypes
)
from deep_translator import GoogleTranslator

BOT_TOKEN = "7869701595:AAEjqBrRwe8FdcEZN-ICy60XAPk586APmDw"
SOURCE_CHANNEL_ID = -1002509471176
TARGET_CHANNEL_ID = -1002133245347
ADMIN_ID = 522888907
SOURCE_TAG = "@Gopaska_boutique_Italyclothing"
DRAFTS_FILE = "drafts.json"

# --- Завантаження чернеток ---
if os.path.exists(DRAFTS_FILE):
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        drafts = json.load(f)
else:
    drafts = {}

def save_drafts():
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

# --- Переклад ---
def translate_to_ukrainian(text):
    try:
        return GoogleTranslator(source='auto', target='uk').translate(text)
    except Exception:
        return text

def add_source_signature(text, forward_from_chat_title):
    if forward_from_chat_title:
        first_word = forward_from_chat_title.split()[0]
        hashtag_tag = f"#{first_word}{SOURCE_TAG}"
    else:
        hashtag_tag = SOURCE_TAG
    return f"{text}\n\n{hashtag_tag}"

def get_draft_keyboard(draft_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("+0", callback_data=f"add|{draft_id}|0"),
            InlineKeyboardButton("+7", callback_data=f"add|{draft_id}|7"),
            InlineKeyboardButton("+10", callback_data=f"add|{draft_id}|10"),
            InlineKeyboardButton("+13", callback_data=f"add|{draft_id}|13"),
        ],
        [
            InlineKeyboardButton("+15", callback_data=f"add|{draft_id}|15"),
            InlineKeyboardButton("+20", callback_data=f"add|{draft_id}|20"),
            InlineKeyboardButton("+25", callback_data=f"add|{draft_id}|25"),
        ],
        [
            InlineKeyboardButton("+30", callback_data=f"add|{draft_id}|30"),
            InlineKeyboardButton("+35", callback_data=f"add|{draft_id}|35"),
            InlineKeyboardButton("+40", callback_data=f"add|{draft_id}|40"),
            InlineKeyboardButton("+50", callback_data=f"add|{draft_id}|50"),
            InlineKeyboardButton("+1", callback_data=f"add|{draft_id}|1"),
        ],
        [
            InlineKeyboardButton("-1", callback_data=f"add|{draft_id}|-1"),
            InlineKeyboardButton("-2", callback_data=f"add|{draft_id}|-2"),
            InlineKeyboardButton("-5", callback_data=f"add|{draft_id}|-5"),
            InlineKeyboardButton("-10", callback_data=f"add|{draft_id}|-10"),
        ],
        [
            InlineKeyboardButton("✏️ Редагувати текст", callback_data=f"edit|{draft_id}"),
            InlineKeyboardButton("➡️ Відправити без змін", callback_data=f"send|{draft_id}"),
            InlineKeyboardButton("❌ Відхилити", callback_data=f"cancel|{draft_id}")
        ]
    ])

# --- Відправка чернетки адміну ---
async def send_draft_preview(context: ContextTypes.DEFAULT_TYPE, draft_id):
    draft = drafts[draft_id]
    value_text = f"💎 Значення: {draft.get('value',0)}"

    # Фото / альбом (тільки перше фото)
    if draft.get("is_album"):
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=draft["photos"][0],
            caption=f"Чернетка (альбом)\n{value_text}"
        )
    else:
        if draft.get("photo"):
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=draft["photo"],
                caption=f"Чернетка\n{value_text}"
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"Чернетка\n{value_text}"
            )

    await asyncio.sleep(0.3)

    # Текст чернетки з кнопками
    keyboard = get_draft_keyboard(draft_id)
    text_to_send = draft.get("original_text") or "Без тексту"

    numbers = re.findall(r"\d+[.,]?\d*", text_to_send)
    index = draft.get("current_index", 0)
    if numbers:
        def replace_number(match):
            replace_number.counter += 1
            n = match.group()
            if replace_number.counter - 1 == index:
                return f"[{n}]"
            return n
        replace_number.counter = 0
        text_to_send = re.sub(r"\d+[.,]?\d*", replace_number, text_to_send)

    sent_text = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📝 Оригінальний текст:\n\n{text_to_send}",
        reply_markup=keyboard
    )
    draft["text_message_id"] = sent_text.message_id
    draft["current_index"] = 0
    save_drafts()

# --- Ловимо повідомлення з каналу ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message.chat_id != SOURCE_CHANNEL_ID:
        return

    forward_from_chat_title = (
        message.forward_from_chat.title if message.forward_from_chat else message.chat.title
    )

    text = message.caption or message.text
    if not text:
        text = "Без тексту"
    text = translate_to_ukrainian(text)
    text = add_source_signature(text, forward_from_chat_title)

    media_group_id = getattr(message, "media_group_id", None)

    if media_group_id:
        if media_group_id not in drafts:
            drafts[media_group_id] = {
                "photos": [],
                "original_text": text,
                "is_album": True,
                "value": 0,
                "current_index": 0
            }
        photo_id = message.photo[-1].file_id if message.photo else None
        if photo_id:
            drafts[media_group_id]["photos"].append(photo_id)
        save_drafts()

        if len(drafts[media_group_id]["photos"]) == 1:
            draft_id = media_group_id
            await send_draft_preview(context, draft_id)
    else:
        photo_id = message.photo[-1].file_id if message.photo else None
        draft_id = str(uuid.uuid4())
        drafts[draft_id] = {
            "photo": photo_id,
            "original_text": text,
            "is_album": False,
            "value": 0,
            "current_index": 0
        }
        save_drafts()
        await send_draft_preview(context, draft_id)

# --- Обробка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]
    draft_id = data[1]

    if draft_id not in drafts:
        await query.edit_message_text("⚠️ Чернетка не знайдена.")
        return

    draft = drafts[draft_id]

    if action == "cancel":
        await query.edit_message_text("❌ Чернетка відхилена")
        del drafts[draft_id]
        save_drafts()
        return

    if action == "send":
        clean_text = re.sub(r"[\[\]]", "", draft.get("original_text") or "Без тексту")
        if draft.get("is_album"):
            media = [InputMediaPhoto(media=pid) for pid in draft["photos"]]
            await context.bot.send_media_group(chat_id=TARGET_CHANNEL_ID, media=media)
            await asyncio.sleep(0.5)
            await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=clean_text)
        elif draft.get("photo"):
            await context.bot.send_photo(chat_id=TARGET_CHANNEL_ID, photo=draft["photo"], caption=clean_text)
        else:
            await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=clean_text)

        await query.edit_message_text("✅ Опубліковано у канал")
        del drafts[draft_id]
        save_drafts()
        return

    if action == "add":
        value_to_add = int(data[2])
        text = draft.get("original_text", "")
        numbers = re.findall(r"\d+[.,]?\d*", text)
        if not numbers:
            await query.answer("⚠️ У тексті немає чисел")
            return

        index = draft.get("current_index", 0)
        num_str = numbers[index]
        try:
            num = float(num_str.replace(',', '.'))
        except:
            num = 0
        new_val = max(0, round(num + value_to_add))
        numbers[index] = str(new_val)

        # Замінюємо текст із виділенням наступного числа
        def replace_number(match):
            replace_number.counter += 1
            n = numbers[replace_number.counter - 1]
            if replace_number.counter - 1 == (index + 1) % len(numbers):
                return f"[{n}]"
            return n
        replace_number.counter = 0
        new_text = re.sub(r"\d+[.,]?\d*", replace_number, text)

        draft["original_text"] = new_text
        draft["current_index"] = (index + 1) % len(numbers)
        save_drafts()

        await context.bot.edit_message_text(
            chat_id=ADMIN_ID,
            message_id=draft["text_message_id"],
            text=f"📝 Оригінальний текст:\n\n{draft['original_text']}",
            reply_markup=get_draft_keyboard(draft_id)
        )
        return

    if action == "edit":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Введіть новий текст для чернетки {draft_id}:")
        context.user_data["edit_draft_id"] = draft_id
        return

# --- Редагування тексту ---
async def edit_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft_id = context.user_data.get("edit_draft_id")
    if not draft_id or draft_id not in drafts:
        return

    new_text = update.message.text or "Без тексту"
    draft = drafts[draft_id]
    draft["original_text"] = new_text
    draft["current_index"] = 0
    save_drafts()

    await context.bot.edit_message_text(
        chat_id=ADMIN_ID,
        message_id=draft["text_message_id"],
        text=f"📝 Оригінальний текст:\n\n{draft['original_text']}",
        reply_markup=get_draft_keyboard(draft_id)
    )

    await update.message.reply_text("✅ Текст чернетки оновлено")
    del context.user_data["edit_draft_id"]

# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), edit_text_handler))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
