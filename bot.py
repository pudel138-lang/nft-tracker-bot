import asyncio
import logging
import json
import os
import time
import random
import string
from datetime import datetime
import html

from flask import Flask, request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== Настройки ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8269202056:AAEsbpsM93ey7C0Zh9dlT6oUKW2a_rFWl5w")
WEBHOOK_HOST = "https://nft-tracker-bot.onrender.com"
WEBHOOK_PATH = f"/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

SOFTWARE_GROUP_LINK = "https://t.me/+um2ZFdJnNnM0Mjhi"
DATA_FILE = "purchases.json"

PRICES = {
    "LITE": {"LIFETIME": 100, "MONTH": 30, "WEEK": 15},
    "VIP": {"LIFETIME": 200, "MONTH": 50, "WEEK": 0},
    "TERMUX": {"LIFETIME": 100, "MONTH": 30, "WEEK": 15},
}

# ========== Логирование ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Инициализация ==========
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальный event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ========== Утилиты ==========
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_data(records):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def gen_key(version):
    s = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    t = int(time.time()) % 100000
    ver = (version or "KEY")[:3].upper()
    return f"{ver}-{s}-{t}"

def pretty_price(price_usd):
    return f"${price_usd}"

def quote_html(text: str) -> str:
    return html.escape(str(text))

# ========== Inline меню ==========
def main_menu_markup():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Купить ключ", callback_data="menu_buy")
    kb.button(text="👤 Профиль", callback_data="menu_profile")
    kb.button(text="💰 Рефералька", callback_data="menu_ref")
    kb.button(text="🇬🇧 English", callback_data="menu_lang_en")
    kb.adjust(2, 2)
    return kb.as_markup()

def versions_markup():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔹 LITE", callback_data="ver_LITE")
    kb.button(text="🔸 VIP", callback_data="ver_VIP")
    kb.button(text="🟢 Termux", callback_data="ver_TERMUX")
    kb.button(text="⬅️ Назад", callback_data="back_main")
    kb.adjust(2, 2)
    return kb.as_markup()

# ========== Хэндлеры ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎯 NFT TRACKER BOT", reply_markup=main_menu_markup())

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"🆔 Your chat_id = {message.from_user.id}")

@dp.callback_query(F.data == "menu_buy")
async def cb_menu_buy(callback: types.CallbackQuery):
    await callback.message.edit_text("💎 Выберите версию:", reply_markup=versions_markup())

@dp.callback_query(F.data == "menu_profile")
async def cb_menu_profile(callback: types.CallbackQuery):
    uid = callback.from_user.id
    text = (
        f"👤 Профиль\n\n"
        f"🆔 ID: <code>{quote_html(uid)}</code>\n"
        "🔑 Ключ: <code>не куплен</code>\n\n"
        f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="back_main")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "menu_ref")
async def cb_menu_ref(callback: types.CallbackQuery):
    uid = callback.from_user.id
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref{uid}"
    text = (
        f"💰 Реферальная система\n\n"
        f"🔗 Твоя ссылка:\n{link}\n\n"
        f"👥 Приглашено: <b>0</b>\n"
        f"💵 Бонус: <b>0 USD</b>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="back_main")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🎯 NFT TRACKER BOT", reply_markup=main_menu_markup())

@dp.callback_query(F.data.startswith("ver_"))
async def cb_select_version(callback: types.CallbackQuery):
    version = callback.data.replace("ver_", "")
    await callback.message.answer(f"🔹 Выбрана версия: {version}")

# Простой обработчик всех сообщений
@dp.message()
async def handle_all_messages(message: types.Message):
    await message.answer("🤖 Используйте /start для начала работы")

# ========== Webhook обработчики ==========
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    try:
        update_data = request.get_json()
        logger.info(f"Получен update: {update_data}")
        
        # Обрабатываем в существующем event loop
        future = asyncio.run_coroutine_threadsafe(
            dp.feed_update(bot, types.Update(**update_data)), 
            loop
        )
        future.result(timeout=10)  # Ждем результат до 10 секунд
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "✅ NFT Tracker Bot is running via Webhook"

@app.route("/set_webhook")
def set_webhook_route():
    try:
        future = asyncio.run_coroutine_threadsafe(set_webhook(), loop)
        result = future.result(timeout=10)
        return f"Webhook установлен: {WEBHOOK_URL}"
    except Exception as e:
        return f"Ошибка: {e}"

@app.route("/check")
def check_webhook():
    try:
        future = asyncio.run_coroutine_threadsafe(bot.get_webhook_info(), loop)
        webhook_info = future.result(timeout=10)
        return {
            "status": "running",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count
        }
    except Exception as e:
        return {"error": str(e)}

# ========== Установка Webhook ==========
async def set_webhook():
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен: {WEBHOOK_URL}")

# ========== Запуск ==========
def start_bot():
    """Запуск бота в фоновом режиме"""
    async def start():
        await set_webhook()
        logger.info("Бот запущен и готов к работе!")
    
    asyncio.run_coroutine_threadsafe(start(), loop)

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    
    # Запускаем бота в фоне
    start_bot()
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
