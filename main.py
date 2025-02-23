import json
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = "7647644799:AAFFGeByDy_a0wb50HgGW__6I4cEg73Nfuc"
ADMIN_IDS = {7818339055}  # Admin ID lar
CHANNELS = {
    -1002486731131: "https://t.me/+nuXRLMGdmQQxNjEy",
    -1002454578945: "https://t.me/+dhk78PwXwFM4YzQy"
}
DB_CONFIG = {
    "user": "postgres",
    "password": "techno",
    "database": "bot_db",
    "host": "localhost"
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 📂 **Ma'lumotlar bazasini yaratish**
async def create_db():
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            file_id TEXT NOT NULL
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.close()

# 📌 **Vaqtincha video saqlash**
pending_videos = {}

# 🟢 **Obunani tekshirish**
async def check_subscription(user_id):
    not_subscribed = []
    for channel_id in CHANNELS.keys():
        try:
            chat_member = await bot.get_chat_member(channel_id, user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(channel_id)
        except:
            not_subscribed.append(channel_id)
    return not_subscribed

# 🟢 **Foydalanuvchini ro'yxatga olish**
@dp.message(Command("start"))
async def register_user(message: types.Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute("INSERT INTO users (id, username, full_name) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING", 
                       user_id, message.from_user.username, message.from_user.full_name)
    await conn.close()
    
    not_subscribed = await check_subscription(user_id)
    if not not_subscribed:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📥 Kodlarni olish", url="https://t.me/kinomania_kodlar")]]
        )
        await message.answer("👋 Salom! Kodni yuboring: ", reply_markup=keyboard)
    else:
        buttons = [
            [InlineKeyboardButton(text="OBUNA BO'LING", url=CHANNELS[channel_id])]
            for channel_id in not_subscribed if channel_id in CHANNELS
        ]
        buttons.append([InlineKeyboardButton(text="✅ TEKSHIRISH", callback_data="check_subscription")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("🚫 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=keyboard)

# ✅ **Tekshirish tugmasi bosilganda obunani qayta tekshirish**
@dp.callback_query(lambda c: c.data == "check_subscription")
async def verify_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    not_subscribed = await check_subscription(user_id)
    
    if not not_subscribed:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📥 Kodlarni olish", url="https://t.me/kinomania_kodlar")]]
        )
        await callback_query.message.edit_text("👋 Salom! Kodni yuboring: ", reply_markup=keyboard)
    else:
        buttons = [
            [InlineKeyboardButton(text="OBUNA BO'LING", url=CHANNELS[channel_id])]
            for channel_id in not_subscribed if channel_id in CHANNELS
        ]
        buttons.append([InlineKeyboardButton(text="✅ TEKSHIRISH", callback_data="check_subscription")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback_query.message.edit_text("🚫 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=keyboard)

# 📥 **Kod bo‘yicha videoni chiqarish**
@dp.message(lambda message: message.text and message.text.isdigit())
async def get_video_by_code(message: types.Message):
    code = message.text.strip()
    conn = await asyncpg.connect(**DB_CONFIG)
    video = await conn.fetchrow("SELECT file_id FROM videos WHERE code = $1", code)
    await conn.close()
    
    if video:
        await message.answer_video(video["file_id"])
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📥 Kodlarni olish", url="https://t.me/kinomania_kodlar")]]
        )
        await message.answer("🚫 Bunday kod mavjud emas!", reply_markup=keyboard)

# 📊 **Statistika**
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    conn = await asyncpg.connect(**DB_CONFIG)
    user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    video_count = await conn.fetchval("SELECT COUNT(*) FROM videos")
    await conn.close()
    await message.answer(f"📊 Bot statistikasi:\n👤 Foydalanuvchilar: {user_count}\n🎥 Yuklangan videolar: {video_count}")

# 📢 **E'lon berish**
@dp.message(Command("elon"))
async def ask_announcement(message: types.Message):
    await message.answer("📢 E’lon matnini 'elon ...' shaklida kiriting!")

@dp.message(lambda message: message.text.lower().startswith("elon "))
async def send_announcement(message: types.Message):
    text = message.text[5:].strip()  # "elon " so‘zini olib tashlash
    conn = await asyncpg.connect(**DB_CONFIG)
    users = await conn.fetch("SELECT id FROM users")
    await conn.close()

    for user in users:
        try:
            await bot.send_message(user["id"], f"📢 E’lon: {text}")
        except:
            pass

    # ✅ **Admin uchun tasdiqlovchi xabar yuboriladi**
    await message.answer("📢 E’lon yuborildi!")

# 📤 **Admin video yuklashi**
@dp.message(Command("video"))
async def ask_video(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🎥 Iltimos, videoni yuboring!")

@dp.message(lambda message: message.video and message.from_user.id in ADMIN_IDS)
async def save_video(message: types.Message):
    video_id = message.video.file_id
    pending_videos[message.from_user.id] = video_id
    await message.answer("✅ Video qabul qilindi! Endi unga kod yuboring.")

# 🚀 **Botni ishga tushirish**
async def main():
    await create_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
