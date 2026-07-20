import asyncio
import aiohttp
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8807365838:AAHd1J0-NilDnNOIqFTdBeoiolYA0_LoPlQ"
API_KEY = "26977b0eb7d225135a9830acf4669a0f"
API_URL = "https://topsmm.com/api/v2"
MARKUP = 1.2  # 20% үстеме
ADMIN_ID = 8078029788

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"
def run_flask(): app.run(host='0.0.0.0', port=8080)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ЖӘНЕ API ---
async def init_db():
    async with aiosqlite.connect("bot_data.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)")
        await db.commit()

async def get_balance(user_id):
    async with aiosqlite.connect("bot_data.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_balance(user_id, amount):
    async with aiosqlite.connect("bot_data.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def call_api(action, **kwargs):
    async with aiohttp.ClientSession() as session:
        params = {'key': API_KEY, 'action': action}
        params.update(kwargs)
        async with session.post(API_URL, data=params) as resp:
            return await resp.json()

# --- МӘЗІР ---
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📈 SMM"), KeyboardButton(text="📱 SMS нөмір")],
    [KeyboardButton(text="💳 Баланс")],
    [KeyboardButton(text="👑 Админ панелі")]
], resize_keyboard=True)

# --- ХАНДЛЕРЛЕР ---
@dp.message(Command("start"))
async def start(message: Message):
    await init_db()
    await message.answer("Сәлем! Біздің ботқа қош келдіңіз. Қызмет таңдаңыз:", reply_markup=main_kb)

@dp.message(F.text == "📈 SMM")
async def smm_services(message: Message):
    services = await call_api("services")
    text = "🔥 Қызметтер тізімі (Тапсырыс беру үшін /order [id] [link] [count]):\n\n"
    for s in services[:10]:
        price = float(s['rate']) * MARKUP
        text += f"ID: {s['service']} | {s['name']} | {price:.2f} ₸\n"
    await message.answer(text)

@dp.message(Command("order"))
async def make_order(message: Message):
    args = message.text.split()
    if len(args) < 4:
        return await message.answer("Формат: /order [id] [link] [count]")
    
    # Баланс тексеру
    bal = await get_balance(message.from_user.id)
    # Болжамды баға есептеу (бұл жерде API-дан бағасын алып тексеру керек)
    # Қарапайымдылық үшін баланс болса жібереді:
    res = await call_api("add", service=args[1], link=args[2], quantity=args[3])
    if 'order' in res:
        await update_balance(message.from_user.id, -100) # Мысалға 100 ₸ алдық
        await message.answer(f"✅ Тапсырыс қабылданды! ID: {res['order']}")
    else:
        await message.answer("❌ Қате: Тапсырыс қабылданбады.")

@dp.message(F.text == "💳 Баланс")
async def balance_menu(message: Message):
    bal = await get_balance(message.from_user.id)
    await message.answer(f"💰 Балансыңыз: {bal} ₸\n\nKaspi: 77471164091 (Аббос П.)\nЧекті жіберіңіз.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
        caption=f"Пайдаланушы: {message.from_user.id}\nБаланс қосу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ 500₸", callback_data=f"add_500_{message.from_user.id}")]
        ]))
    await message.answer("Чек жіберілді. Админ растаған соң баланс түседі.")

@dp.callback_query(F.data.startswith("add_"))
async def approve(call: types.CallbackQuery):
    data = call.data.split("_")
    await update_balance(int(data[2]), int(data[1]))
    await call.message.edit_caption(caption="✅ Баланс қосылды!")
    await bot.send_message(int(data[2]), f"✅ Балансыңызға {data[1]} ₸ қосылды.")

async def main():
    Thread(target=run_flask).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
