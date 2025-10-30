import logging
import json
import os
import time
import random
import string
import html
import requests
from flask import Flask, request, jsonify

# ========== Настройки ==========
BOT_TOKEN = "8269202056:AAEsbpsM93ey7C0Zh9dlT6oUKW2a_rFWl5w"
WEBHOOK_URL = f"https://nft-tracker-bot.onrender.com/webhook/{BOT_TOKEN}"

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

def send_telegram_message(chat_id, text, reply_markup=None):
    """Отправка сообщения через Telegram API"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    try:
        response = requests.post(url, json=data)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False

def edit_telegram_message(chat_id, message_id, text, reply_markup=None):
    """Редактирование сообщения через Telegram API"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText'
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    try:
        response = requests.post(url, json=data)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения: {e}")
        return False

# ========== Inline меню ==========
def main_menu_markup():
    return {
        "inline_keyboard": [
            [
                {"text": "🛒 Купить ключ", "callback_data": "menu_buy"},
                {"text": "👤 Профиль", "callback_data": "menu_profile"}
            ],
            [
                {"text": "💰 Рефералька", "callback_data": "menu_ref"},
                {"text": "🇬🇧 English", "callback_data": "menu_lang_en"}
            ]
        ]
    }

def versions_markup():
    return {
        "inline_keyboard": [
            [
                {"text": "🔹 LITE", "callback_data": "ver_LITE"},
                {"text": "🔸 VIP", "callback_data": "ver_VIP"}
            ],
            [
                {"text": "🟢 Termux", "callback_data": "ver_TERMUX"},
                {"text": "⬅️ Назад", "callback_data": "back_main"}
            ]
        ]
    }

def back_button_markup():
    return {
        "inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": "back_main"}]]
    }

# ========== Обработчики ==========
def handle_start(chat_id, first_name):
    text = f"🎯 NFT TRACKER BOT\n\nПривет, {first_name}!"
    send_telegram_message(chat_id, text, main_menu_markup())

def handle_id(chat_id):
    send_telegram_message(chat_id, f"🆔 Your chat_id = {chat_id}")

def handle_menu_buy(chat_id, message_id):
    edit_telegram_message(chat_id, message_id, "💎 Выберите версию:", versions_markup())

def handle_menu_profile(chat_id, message_id, user_id):
    text = (
        f"👤 Профиль\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        "🔑 Ключ: <code>не куплен</code>\n\n"
        f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}"
    )
    edit_telegram_message(chat_id, message_id, text, back_button_markup())

def handle_menu_ref(chat_id, message_id, user_id):
    # Используем фиксированное имя бота, так как не можем асинхронно получить информацию
    bot_username = "nft_tracker_soft_bot"  # замени на реальный username бота
    link = f"https://t.me/{bot_username}?start=ref{user_id}"
    text = (
        f"💰 Реферальная система\n\n"
        f"🔗 Твоя ссылка:\n{link}\n\n"
        f"👥 Приглашено: <b>0</b>\n"
        f"💵 Бонус: <b>0 USD</b>"
    )
    edit_telegram_message(chat_id, message_id, text, back_button_markup())

def handle_back_main(chat_id, message_id):
    edit_telegram_message(chat_id, message_id, "🎯 NFT TRACKER BOT", main_menu_markup())

def handle_select_version(chat_id, version):
    send_telegram_message(chat_id, f"🔹 Выбрана версия: {version}")

def handle_echo(chat_id, text):
    send_telegram_message(chat_id, f"🤖 Вы написали: {text}\n\nИспользуйте /start для начала работы")

# ========== Webhook обработчики ==========
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update_data = request.get_json()
        logger.info("Получен update от Telegram")
        
        # Обрабатываем сообщение
        if "message" in update_data:
            message = update_data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            if text.startswith("/start"):
                handle_start(chat_id, message["from"].get("first_name", "Пользователь"))
            elif text.startswith("/id"):
                handle_id(chat_id)
            elif text.startswith("/"):
                handle_echo(chat_id, text)
            else:
                handle_echo(chat_id, text)
                
        # Обрабатываем callback queries (кнопки)
        elif "callback_query" in update_data:
            callback = update_data["callback_query"]
            data = callback["data"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            user_id = callback["from"]["id"]
            
            if data == "menu_buy":
                handle_menu_buy(chat_id, message_id)
            elif data == "menu_profile":
                handle_menu_profile(chat_id, message_id, user_id)
            elif data == "menu_ref":
                handle_menu_ref(chat_id, message_id, user_id)
            elif data == "back_main":
                handle_back_main(chat_id, message_id)
            elif data.startswith("ver_"):
                version = data.replace("ver_", "")
                handle_select_version(chat_id, version)
            elif data == "menu_lang_en":
                edit_telegram_message(chat_id, message_id, "✅ Language changed to English", back_button_markup())
            
            # Ответ на callback query (убираем "часики")
            requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery', 
                         json={'callback_query_id': callback['id']})
        
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
        response = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}')
        return f"Webhook установлен: {WEBHOOK_URL}<br>Response: {response.text}"
    except Exception as e:
        return f"Ошибка: {e}"

@app.route("/check")
def check_webhook():
    try:
        response = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo')
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ========== Запуск ==========
if __name__ == "__main__":
    print("🚀 Запуск бота...")
    
    # Устанавливаем webhook при старте
    try:
        requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook')
        requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}')
        print("✅ Webhook установлен")
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
