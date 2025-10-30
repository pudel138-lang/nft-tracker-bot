import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
import os

# ========== НАСТРОЙКИ ==========
TOKEN = "ТВОЙ_ТОКЕН_ОТ_БОТА"
WEBHOOK_URL = f"https://nft-tracker-bot.onrender.com/telegram/webhook/{TOKEN}"

# Flask приложение
app = Flask(__name__)

# Создаем объекты aiogram
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@dp.message()
async def handle_message(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Бот работает ✅")

# ========== ВЕБХУК ==========
@app.route(f"/telegram/webhook/{TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update_data = request.get_json()
        update = Update.model_validate(update_data)
        asyncio.run(dp.feed_update(bot, update))
    except Exception as e:
        print(f"Ошибка обработки Telegram webhook: {e}")
    return "ok", 200

# ========== ГЛАВНАЯ СТРАНИЦА ==========
@app.route("/")
def index():
    return "✅ NFT Tracker Bot is running via Webhook"

# ========== УСТАНОВКА ВЕБХУКА ==========
async def set_webhook():
    webhook = await bot.get_webhook_info()
    if webhook.url != WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook установлен: {WEBHOOK_URL}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Запуск Flask + aiogram webhook...")
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
