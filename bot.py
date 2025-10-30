import logging
import json
import os
import time
import random
import string
import html
import base64
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, request, jsonify

# ========== Настройки ==========
BOT_TOKEN = "8269202056:AAEsbpsM93ey7C0Zh9dlT6oUKW2a_rFWl5w"
WEBHOOK_URL = f"https://nft-tracker-bot.onrender.com/webhook/{BOT_TOKEN}"

# CryptoBot API настройки (получи в @CryptoBot)
CRYPTOBOT_TOKEN = "480624:AAumVGyvHpmnmTKE5SB71VqMnT7EESjojse"  # Получи в @CryptoBot через /start
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

SOFTWARE_GROUP_LINK = "https://t.me/+um2ZFdJnNnM0Mjhi"
DATA_FILE = "purchases.json"

PRICES = {
    "LITE": {"LIFETIME": 100, "MONTH": 30, "WEEK": 15},
    "VIP": {"LIFETIME": 200, "MONTH": 50, "WEEK": 0},
    "TERMUX": {"LIFETIME": 100, "MONTH": 30, "WEEK": 15},
}

# Фото для каждой версии
VERSION_PHOTOS = {
    "LITE": "lite.jpg",
    "VIP": "vip.jpg", 
    "TERMUX": "termux.jpg"
}

VERSION_DESCRIPTIONS = {
    "LITE": "🔹 <b>LITE версия</b>\n\n• Базовый функционал\n• Отслеживание NFT\n• Уведомления\n• Поддержка 10 коллекций",
    "VIP": "🔸 <b>VIP версия</b>\n\n• Все функции LITE\n• Расширенная аналитика\n• Приоритетная поддержка\n• Неограниченное количество коллекций\n• Эксклюзивные фичи",
    "TERMUX": "🟢 <b>Termux версия</b>\n\n• Работа на Android\n• Автономный режим\n• Низкое потребление ресурсов\n• Фоновый режим"
}

# ========== Логирование ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Инициализация ==========
app = Flask(__name__)

# ========== CryptoBot API ==========
def cryptobot_request(method, data=None):
    """Запрос к CryptoBot API"""
    try:
        url = f"{CRYPTOBOT_API_URL}/{method}"
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN,
            'Content-Type': 'application/json'
        }
        
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req = Request(url, data=json_data, headers=headers)
        else:
            req = Request(url, headers=headers)
        
        with urlopen(req) as response:
            result = json.loads(response.read().decode())
            if result.get('ok'):
                return result.get('result')
            else:
                logger.error(f"CryptoBot API error: {result}")
                return None
    except Exception as e:
        logger.error(f"CryptoBot request error: {e}")
        return None

def create_cryptobot_invoice(amount, asset="USDT", description="", hidden_message=""):
    """Создание инвойса в CryptoBot"""
    data = {
        "asset": asset,
        "amount": str(amount),
        "description": description,
        "hidden_message": hidden_message,
        "paid_btn_name": "callback",
        "paid_btn_url": "https://t.me/nft_tracker_soft_bot",
        "allow_comments": False,
        "allow_anonymous": False
    }
    
    return cryptobot_request("createInvoice", data)

def check_cryptobot_invoice(invoice_id):
    """Проверка статуса инвойса"""
    return cryptobot_request("getInvoices", {"invoice_ids": invoice_id})

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

def make_telegram_request(method, data=None):
    """Делает запрос к Telegram API"""
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/{method}'
        
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req = Request(url, data=json_data, headers={'Content-Type': 'application/json'})
        else:
            req = Request(url)
        
        with urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Ошибка запроса к Telegram: {e}")
        return None

def send_telegram_message(chat_id, text, reply_markup=None):
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    return make_telegram_request('sendMessage', data)

def send_telegram_photo(chat_id, photo_path, caption, reply_markup=None):
    """Отправка фото через Telegram API"""
    try:
        with open(photo_path, 'rb') as photo_file:
            photo_data = photo_file.read()
        
        # Кодируем в base64 для отправки
        photo_b64 = base64.b64encode(photo_data).decode('utf-8')
        
        data = {
            'chat_id': chat_id,
            'photo': f"data:image/jpeg;base64,{photo_b64}",
            'caption': caption,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = reply_markup
            
        return make_telegram_request('sendPhoto', data)
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        # Если фото не найдено, отправляем текстовое сообщение
        return send_telegram_message(chat_id, caption, reply_markup)

def edit_telegram_message(chat_id, message_id, text, reply_markup=None):
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    return make_telegram_request('editMessageText', data)

def answer_callback_query(callback_query_id, text=None):
    data = {'callback_query_id': callback_query_id}
    if text:
        data['text'] = text
    return make_telegram_request('answerCallbackQuery', data)

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

def plan_markup(version):
    tariffs = PRICES.get(version, {})
    buttons = []
    
    for plan_key, price in tariffs.items():
        if price and price > 0:
            label = f"{plan_key} - ${price}"
            callback_data = f"plan_{version}_{plan_key}_{price}"
            buttons.append([{"text": label, "callback_data": callback_data}])
    
    buttons.append([{"text": "⬅️ Назад", "callback_data": "menu_buy"}])
    
    return {"inline_keyboard": buttons}

def payment_markup(version, plan, price):
    return {
        "inline_keyboard": [
            [
                {"text": "💳 CryptoBot (USDT)", "callback_data": f"pay_crypto_{version}_{plan}_{price}"},
            ],
            [
                {"text": "⬅️ Назад", "callback_data": f"ver_{version}"}
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
    data = load_data()
    last_purchase = None
    
    for purchase in reversed(data):
        if str(purchase.get("user_id")) == str(user_id):
            last_purchase = purchase
            break
    
    if last_purchase:
        text = (
            f"👤 Профиль\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"🔑 Ключ: <code>{last_purchase.get('key', 'не куплен')}</code>\n"
            f"⚙ Версия: {last_purchase.get('version', 'не указана')}\n"
            f"📦 План: {last_purchase.get('plan', 'не указан')}\n"
            f"💲 Цена: ${last_purchase.get('price', '0')}\n"
            f"📅 Дата: {last_purchase.get('created_at', 'не указана')}\n\n"
            f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}"
        )
    else:
        text = (
            f"👤 Профиль\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            "🔑 Ключ: <code>не куплен</code>\n\n"
            f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}"
        )
    edit_telegram_message(chat_id, message_id, text, back_button_markup())

def handle_menu_ref(chat_id, message_id, user_id):
    bot_username = "nft_tracker_soft_bot"
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

def handle_select_version(chat_id, message_id, version):
    """Показ версии с фото и описанием"""
    photo_path = VERSION_PHOTOS.get(version)
    description = VERSION_DESCRIPTIONS.get(version, f"Версия {version}")
    
    if photo_path and os.path.exists(photo_path):
        # Отправляем фото с описанием
        caption = f"{description}\n\n💎 Выберите тарифный план:"
        send_telegram_photo(chat_id, photo_path, caption, plan_markup(version))
        
        # Удаляем предыдущее сообщение с меню
        make_telegram_request('deleteMessage', {
            'chat_id': chat_id,
            'message_id': message_id
        })
    else:
        # Если фото нет, отправляем текстовое сообщение
        text = f"{description}\n\n💎 Выберите тарифный план:"
        edit_telegram_message(chat_id, message_id, text, plan_markup(version))

def handle_select_plan(chat_id, message_id, version, plan, price):
    text = (
        f"🛒 Оформление заказа\n\n"
        f"⚙ Версия: <b>{version}</b>\n"
        f"📦 Тариф: <b>{plan}</b>\n"
        f"💲 Сумма: <b>${price}</b>\n\n"
        f"Выберите способ оплаты:"
    )
    edit_telegram_message(chat_id, message_id, text, payment_markup(version, plan, price))

def handle_payment(chat_id, message_id, version, plan, price, payment_method):
    """Создание инвойса для оплаты"""
    if payment_method == "crypto":
        # Создаем инвойс в CryptoBot
        description = f"NFT Tracker - {version} {plan}"
        hidden_message = f"User: {chat_id}, Version: {version}, Plan: {plan}"
        
        invoice = create_cryptobot_invoice(
            amount=price,
            asset="USDT",
            description=description,
            hidden_message=hidden_message
        )
        
        if invoice and invoice.get('pay_url'):
            # Сохраняем информацию о инвойсе
            invoice_data = {
                "invoice_id": invoice['invoice_id'],
                "user_id": chat_id,
                "version": version,
                "plan": plan,
                "price": price,
                "status": "pending",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pay_url": invoice['pay_url']
            }
            
            # Сохраняем в ожидающие платежи
            pending_data = load_pending_payments()
            pending_data.append(invoice_data)
            save_pending_payments(pending_data)
            
            text = (
                f"💳 Оплата через CryptoBot\n\n"
                f"⚙ Версия: <b>{version}</b>\n"
                f"📦 Тариф: <b>{plan}</b>\n"
                f"💲 Сумма: <b>${price} USDT</b>\n\n"
                f"Для оплаты нажмите на кнопку ниже:\n"
                f"⏰ Счет действителен 15 минут"
            )
            
            markup = {
                "inline_keyboard": [
                    [{"text": "💳 Оплатить сейчас", "url": invoice['pay_url']}],
                    [{"text": "🔄 Проверить оплату", "callback_data": f"check_payment_{invoice['invoice_id']}"}],
                    [{"text": "❌ Отменить", "callback_data": f"cancel_payment_{invoice['invoice_id']}"}]
                ]
            }
            
            edit_telegram_message(chat_id, message_id, text, markup)
        else:
            text = "❌ Ошибка создания счета. Попробуйте позже."
            edit_telegram_message(chat_id, message_id, text)

def handle_check_payment(chat_id, message_id, invoice_id):
    """Проверка статуса оплаты"""
    invoice = check_cryptobot_invoice(invoice_id)
    
    if invoice and len(invoice) > 0:
        invoice_data = invoice[0]
        
        if invoice_data.get('status') == 'paid':
            # Оплата прошла успешно
            handle_successful_payment(chat_id, message_id, invoice_id, invoice_data)
        else:
            # Оплата еще не прошла
            answer_callback_query(chat_id, "⏳ Оплата еще не поступила. Нажмите 'Проверить оплату' через минуту.")
    else:
        answer_callback_query(chat_id, "❌ Ошибка проверки платежа.")

def handle_successful_payment(chat_id, message_id, invoice_id, invoice_data):
    """Обработка успешной оплаты"""
    # Находим данные о заказе
    pending_data = load_pending_payments()
    order_data = None
    
    for order in pending_data:
        if order.get('invoice_id') == invoice_id:
            order_data = order
            break
    
    if order_data:
        # Генерируем ключ
        key = gen_key(order_data['version'])
        
        # Сохраняем покупку
        purchase_data = {
            "user_id": chat_id,
            "version": order_data['version'],
            "plan": order_data['plan'],
            "price": order_data['price'],
            "key": key,
            "payment_method": "cryptobot",
            "status": "paid",
            "invoice_id": invoice_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        data = load_data()
        data.append(purchase_data)
        save_data(data)
        
        # Удаляем из ожидающих
        pending_data = [order for order in pending_data if order.get('invoice_id') != invoice_id]
        save_pending_payments(pending_data)
        
        # Показываем фото версии с ключом
        photo_path = VERSION_PHOTOS.get(order_data['version'])
        caption = (
            f"✅ Оплата подтверждена!\n\n"
            f"⚙ Версия: <b>{order_data['version']}</b>\n"
            f"📦 Тариф: <b>{order_data['plan']}</b>\n"
            f"💲 Сумма: <b>${order_data['price']}</b>\n"
            f"🔑 Ваш ключ: <code>{key}</code>\n\n"
            f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}\n\n"
            f"⚠️ Сохраните ключ в надежном месте!"
        )
        
        if photo_path and os.path.exists(photo_path):
            send_telegram_photo(chat_id, photo_path, caption)
        else:
            send_telegram_message(chat_id, caption)

def handle_echo(chat_id, text):
    send_telegram_message(chat_id, f"🤖 Вы написали: {text}\n\nИспользуйте /start для начала работы")

def load_pending_payments():
    """Загрузка ожидающих платежей"""
    pending_file = "pending_payments.json"
    if not os.path.exists(pending_file):
        return []
    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_pending_payments(records):
    """Сохранение ожидающих платежей"""
    pending_file = "pending_payments.json"
    with open(pending_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

# ========== Webhook обработчики ==========
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update_data = request.get_json()
        logger.info("Получен update от Telegram")
        
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
                
        elif "callback_query" in update_data:
            callback = update_data["callback_query"]
            data = callback["data"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            user_id = callback["from"]["id"]
            
            # Основное меню
            if data == "menu_buy":
                handle_menu_buy(chat_id, message_id)
            elif data == "menu_profile":
                handle_menu_profile(chat_id, message_id, user_id)
            elif data == "menu_ref":
                handle_menu_ref(chat_id, message_id, user_id)
            elif data == "back_main":
                handle_back_main(chat_id, message_id)
            
            # Выбор версии
            elif data.startswith("ver_"):
                version = data.replace("ver_", "")
                handle_select_version(chat_id, message_id, version)
            
            # Выбор тарифа
            elif data.startswith("plan_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    version = parts[1]
                    plan = parts[2]
                    price = parts[3]
                    handle_select_plan(chat_id, message_id, version, plan, price)
            
            # Оплата
            elif data.startswith("pay_"):
                parts = data.split("_")
                if len(parts) >= 5:
                    payment_method = parts[1]
                    version = parts[2]
                    plan = parts[3]
                    price = parts[4]
                    handle_payment(chat_id, message_id, version, plan, price, payment_method)
            
            # Проверка оплаты
            elif data.startswith("check_payment_"):
                invoice_id = data.replace("check_payment_", "")
                handle_check_payment(chat_id, message_id, invoice_id)
            
            # Отмена оплаты
            elif data.startswith("cancel_payment_"):
                invoice_id = data.replace("cancel_payment_", "")
                pending_data = load_pending_payments()
                pending_data = [order for order in pending_data if order.get('invoice_id') != invoice_id]
                save_pending_payments(pending_data)
                edit_telegram_message(chat_id, message_id, "❌ Оплата отменена", main_menu_markup())
            
            # Смена языка
            elif data == "menu_lang_en":
                edit_telegram_message(chat_id, message_id, "✅ Language changed to English", back_button_markup())
            
            answer_callback_query(callback['id'])
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return "Error", 500

# ========== CryptoBot Webhook ==========
@app.route("/cryptobot/webhook", methods=["POST"])
def cryptobot_webhook():
    """Webhook от CryptoBot для уведомлений о платежах"""
    try:
        data = request.get_json()
        logger.info(f"CryptoBot webhook: {data}")
        return "OK", 200
    except Exception as e:
        logger.error(f"CryptoBot webhook error: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "✅ NFT Tracker Bot is running via Webhook"

@app.route("/set_webhook")
def set_webhook_route():
    try:
        webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
        with urlopen(webhook_url) as response:
            result = json.loads(response.read().decode())
            return f"Webhook установлен: {WEBHOOK_URL}<br>Response: {result}"
    except Exception as e:
        return f"Ошибка: {e}"

@app.route("/check")
def check_webhook():
    try:
        with urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo") as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

# ========== Запуск ==========
if __name__ == "__main__":
    print("🚀 Запуск бота с реальной оплатой...")
    
    # Устанавливаем webhook при старте
    try:
        urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}")
        print("✅ Webhook установлен")
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
