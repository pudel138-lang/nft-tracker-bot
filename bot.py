import asyncio
import logging
import threading
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
from aiogram.types import FSInputFile
import aiohttp

# ========== Настройки ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8269202056:AAEsbpsM93ey7C0Zh9dlT6oUKW2a_rFWl5w")
CRYPTOPAY_TOKEN = os.getenv("CRYPTOPAY_TOKEN", "480624:AAumVGyvHpmnmTKE5SB71VqMnT7EESjojse")
WEBHOOK_HOST = "https://nft-tracker-bot.onrender.com"  # твой Render-домен
WEBHOOK_PATH = f"/telegram/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

SOFTWARE_GROUP_LINK = "https://t.me/+um2ZFdJnNnM0Mjhi"

IMG_LITE = "lite.jpg"
IMG_VIP = "vip.jpg"
IMG_TERMUX = "termux.jpg"
DATA_FILE = "purchases.json"

PRICES = {
    "LITE": {"LIFETIME": 100, "MONTH": 30, "WEEK": 15},
    "VIP": {"LIFETIME": 200, "MONTH": 50, "WEEK": 0},
    "TERMUX": {"LIFETIME": 100, "MONTH": 30, "WEEK": 15},
}
DEFAULT_ASSET = "USDT"

# ========== Логирование ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Инициализация ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

main_loop = asyncio.new_event_loop()
asyncio.set_event_loop(main_loop)

pending_invoices = {}

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

def append_purchase(record):
    data = load_data()
    data.append(record)
    save_data(data)

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

def plan_markup(version):
    kb = InlineKeyboardBuilder()
    v = version.upper()
    tariffs = PRICES.get(v, {})
    for plan_key, price in tariffs.items():
        if price and price > 0:
            label = f"{plan_key.capitalize()} — {pretty_price(price)}"
            cb = f"order|{v}|{plan_key}|{price}"
            kb.button(text=label, callback_data=cb)
    kb.button(text="⬅️ Назад", callback_data="menu_buy")
    kb.adjust(2, 2)
    return kb.as_markup()

# ========== Хэндлеры ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("NFT TRACKER", reply_markup=main_menu_markup())

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"Your chat_id = {message.from_user.id}")

@dp.callback_query(F.data == "menu_buy")
async def cb_menu_buy(callback: types.CallbackQuery):
    await callback.message.edit_text("💎 Выберите версию:", reply_markup=versions_markup())

@dp.callback_query(F.data == "menu_profile")
async def cb_menu_profile(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = load_data()
    last = None
    for rec in reversed(data):
        if int(rec.get("user_id") or 0) == int(uid):
            last = rec
            break
    if last:
        text = (
            f"👤 Профиль\n\n"
            f"🆔 ID: <code>{quote_html(uid)}</code>\n"
            f"🔑 Ключ: <code>{quote_html(last.get('key'))}</code>\n"
            f"⚙ Версия: {quote_html(last.get('version'))}\n"
            f"📦 План: {quote_html(last.get('plan'))}\n"
            f"💲 Цена: {quote_html(last.get('price'))}\n"
            f"📅 Дата: {quote_html(last.get('created_at'))}\n\n"
            f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}"
        )
    else:
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

@dp.callback_query(F.data == "menu_lang_en")
async def cb_menu_lang_en(callback: types.CallbackQuery):
    text = "✅ Language changed to English."
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="back_main")
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: types.CallbackQuery):
    await callback.message.edit_text("NFT TRACKER", reply_markup=main_menu_markup())

# ========== Flask webhook от Telegram ==========
@app.route(WEBHOOK_PATH, methods=["POST"])
async def telegram_webhook():
    try:
        update = types.Update(**request.json)
        await dp.process_update(update)
    except Exception as e:
        logger.exception(f"Ошибка обработки Telegram webhook: {e}")
    return "OK", 200

# ========== Flask webhook от CryptoPay ==========
@app.route("/cryptopay/webhook", methods=["POST"])
def cryptopay_webhook():
    data = request.get_json(force=True)
    logger.info("Webhook получен: %s", data)
    return "ok", 200

# ========== Установка Webhook при старте ==========
@app.before_first_request
def setup_webhook():
    async def set_hook():
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook установлен: {WEBHOOK_URL}")

    asyncio.run(set_hook())

# ========== Главная страница ==========
@app.route('/')
def index():
    return "✅ NFT Tracker Bot is running via Webhook", 200

# ========== Запуск ==========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
