import logging
import json
import os
import time
import random
import string
import html
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, request, jsonify

# ========== Настройки ==========
BOT_TOKEN = "8269202056:AAEsbpsM93ey7C0Zh9dlT6oUKW2a_rFWl5w"
WEBHOOK_URL = f"https://nft-tracker-bot.onrender.com/webhook/{BOT_TOKEN}"

# CryptoBot API настройки
CRYPTOBOT_TOKEN = "480624:AAumVGyvHpmnmTKE5SB71VqMnT7EESjojse"
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

SOFTWARE_GROUP_LINK = "https://t.me/+um2ZFdJnNnM0Mjhi"
DATA_FILE = "purchases.json"
PENDING_FILE = "pending_payments.json"

# Единые цены для всех продуктов
UNIFIED_PRICES = {
    "WEEK": 5,      # 7 дней
    "TWO_WEEKS": 10,  # 14 дней
    "MONTH": 15,    # 31 день
    "LIFETIME": 30  # вечный доступ
}

PRICES = {
    "LITE": UNIFIED_PRICES,
    "VIP": UNIFIED_PRICES,
    "TERMUX": UNIFIED_PRICES,
    "IPA": UNIFIED_PRICES
}

PERIOD_NAMES = {
    "WEEK": "7 дней",
    "TWO_WEEKS": "14 дней",
    "MONTH": "31 день",
    "LIFETIME": "LIFETIME"
}

VERSION_DESCRIPTIONS = {
    "LITE": "🔹 <b>LITE версия</b>\n\n• Базовый функционал\n• Отслеживание NFT\n• Уведомления\n• Поддержка 10 коллекций",
    "VIP": "🔸 <b>VIP версия</b>\n\n• Все функции LITE\n• Расширенная аналитика\n• Приоритетная поддержка\n• Неограниченное количество коллекций\n• Эксклюзивные фичи",
    "TERMUX": "🟢 <b>Termux версия</b>\n\n• Работа на Android\n• Автономный режим\n• Низкое потребление ресурсов\n• Фоновый режим",
    "IPA": "🍎 <b>IPA версия (iPhone)</b>\n\n• Работа на iOS (iPhone)\n• Автономный режим\n• Низкое потребление ресурсов\n• Фоновый режим\n• Оптимизировано для iOS"
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
            return result
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
        "paid_btn_name": "viewItem",
        "paid_btn_url": "https://t.me/nft_tracker_soft_bot",
        "allow_comments": False,
        "allow_anonymous": False,
        "expires_in": 3600  # 1 час
    }
    
    result = cryptobot_request("createInvoice", data)
    if result and result.get('ok'):
        return result.get('result')
    return None

def get_invoice_status(invoice_id):
    """Получение статуса инвойса"""
    try:
        result = cryptobot_request("getInvoices", {"invoice_ids": str(invoice_id)})
        if result and result.get('ok') and result.get('result'):
            invoices = result['result']['items']
            if invoices:
                return invoices[0]
        else:
            logger.error(f"CryptoBot API error: {result}")
            return None
    except Exception as e:
        logger.error(f"Error getting invoice status: {e}")
        return None

# ========== Утилиты ==========
def load_data(filename):
    """Загрузка данных из файла"""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_data(filename, records):
    """Сохранение данных в файл"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def gen_key(version):
    s = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    t = int(time.time()) % 100000
    ver = (version or "KEY")[:3].upper()
    return f"{ver}-{s}-{t}"

def quote_html(text: str) -> str:
    return html.escape(str(text))

def make_telegram_request(method, data=None):
    """Запрос к Telegram API"""
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

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    data = {
        'callback_query_id': callback_query_id,
        'show_alert': show_alert
    }
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
                {"text": "🍎 IPA (iPhone)", "callback_data": "ver_IPA"}
            ],
            [
                {"text": "⬅️ Назад", "callback_data": "back_main"}
            ]
        ]
    }

def plan_markup(version):
    """Клавиатура выбора тарифа с новыми периодами"""
    buttons = []
    
    for plan_key, price in UNIFIED_PRICES.items():
        label = f"{PERIOD_NAMES.get(plan_key, plan_key)} - ${price}"
        callback_data = f"plan_{version}_{plan_key}_{price}"
        buttons.append([{"text": label, "callback_data": callback_data}])
    
    buttons.append([{"text": "⬅️ Назад", "callback_data": "menu_buy"}])
    
    return {"inline_keyboard": buttons}

def payment_method_markup(version, plan, price):
    """Клавиатура выбора способа оплаты"""
    return {
        "inline_keyboard": [
            [
                {"text": "💎 Crypto (USDT)", "callback_data": f"pay_crypto_{version}_{plan}_{price}"},
                {"text": "₽ Рубли", "callback_data": f"pay_rub_{version}_{plan}_{price}"}
            ],
            [{"text": "⬅️ Назад", "callback_data": f"ver_{version}"}]
        ]
    }

def payment_markup(version, plan, price, pay_url):
    """Клавиатура для оплаты через CryptoBot"""
    return {
        "inline_keyboard": [
            [{"text": "💳 Оплатить через CryptoBot", "url": pay_url}],
            [{"text": "🔄 Проверить оплату", "callback_data": f"check_{version}_{plan}_{price}"}],
            [{"text": "❌ Отменить", "callback_data": "back_main"}]
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
    data = load_data(DATA_FILE)
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
            f"📦 План: {PERIOD_NAMES.get(last_purchase.get('plan', ''), last_purchase.get('plan', 'не указан'))}\n"
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
    description = VERSION_DESCRIPTIONS.get(version, f"Версия {version}")
    text = f"{description}\n\n💎 Выберите тарифный план:"
    edit_telegram_message(chat_id, message_id, text, plan_markup(version))

def handle_select_plan(chat_id, message_id, version, plan, price):
    """Показываем выбор способа оплаты"""
    text = (
        f"🛒 Оформление заказа\n\n"
        f"⚙ Версия: <b>{version}</b>\n"
        f"📦 Тариф: <b>{PERIOD_NAMES.get(plan, plan)}</b>\n"
        f"💲 Сумма: <b>${price}</b>\n\n"
        f"Выберите способ оплаты:"
    )
    edit_telegram_message(chat_id, message_id, text, payment_method_markup(version, plan, price))

def handle_pay_crypto(chat_id, message_id, version, plan, price):
    """Оплата через CryptoBot"""
    text = (
        f"💳 Оплата через CryptoBot\n\n"
        f"⚙ Версия: <b>{version}</b>\n"
        f"📦 Тариф: <b>{PERIOD_NAMES.get(plan, plan)}</b>\n"
        f"💲 Сумма: <b>${price} USDT</b>\n\n"
        f"Создаем счет для оплаты..."
    )
    edit_telegram_message(chat_id, message_id, text)
    
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
        pay_url = invoice['pay_url']
        
        # Сохраняем в ожидающие платежи
        pending_data = load_data(PENDING_FILE)
        pending_data.append({
            "invoice_id": invoice['invoice_id'],
            "user_id": chat_id,
            "version": version,
            "plan": plan,
            "price": price,
            "message_id": message_id,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pay_url": pay_url,
            "payment_method": "crypto"
        })
        save_data(PENDING_FILE, pending_data)
        
        text = (
            f"💳 Оплата через CryptoBot\n\n"
            f"⚙ Версия: <b>{version}</b>\n"
            f"📦 Тариф: <b>{PERIOD_NAMES.get(plan, plan)}</b>\n"
            f"💲 Сумма: <b>${price} USDT</b>\n\n"
            f"Для оплаты нажмите кнопку ниже:\n"
            f"⏰ Счет действителен 1 час"
        )
        
        edit_telegram_message(chat_id, message_id, text, payment_markup(version, plan, price, pay_url))
    else:
        text = "❌ Ошибка создания счета. Попробуйте позже."
        edit_telegram_message(chat_id, message_id, text)

def handle_pay_rub(chat_id, message_id, version, plan, price):
    """Оплата в рублях"""
    text = (
        f"₽ Оплата в рублях\n\n"
        f"⚙ Версия: <b>{version}</b>\n"
        f"📦 Тариф: <b>{PERIOD_NAMES.get(plan, plan)}</b>\n"
        f"💲 Сумма: <b>${price}</b>\n\n"
        f"<b>Для оплаты в рублях напишите владельцу:</b>\n"
        f"👉 @scamdura\n\n"
        f"Укажите в сообщении:\n"
        f"• Версию: {version}\n"
        f"• Тариф: {PERIOD_NAMES.get(plan, plan)}\n"
        f"• Ваш ID: <code>{chat_id}</code>"
    )
    
    edit_telegram_message(chat_id, message_id, text, back_button_markup())

def handle_check_payment(chat_id, message_id, version, plan, price, callback_query_id):
    """Проверка статуса оплаты"""
    logger.info(f"Checking payment: chat_id={chat_id}, version={version}, plan={plan}, price={price}")
    
    # Находим заказ по данным
    pending_data = load_data(PENDING_FILE)
    order_data = None
    order_index = -1
    
    for i, order in enumerate(pending_data):
        if (order.get('user_id') == chat_id and 
            order.get('version') == version and 
            order.get('plan') == plan and 
            str(order.get('price')) == str(price)):
            order_data = order
            order_index = i
            break
    
    if not order_data:
        answer_callback_query(callback_query_id, "❌ Заказ не найден")
        return
    
    invoice_id = order_data.get('invoice_id')
    invoice = get_invoice_status(invoice_id)
    
    if not invoice:
        answer_callback_query(callback_query_id, "❌ Ошибка проверки платежа")
        return
    
    status = invoice.get('status', 'active')
    
    if status == 'paid':
        # Генерируем ключ
        key = gen_key(version)
        
        # Сохраняем покупку
        purchase_data = {
            "user_id": chat_id,
            "version": version,
            "plan": plan,
            "price": price,
            "key": key,
            "payment_method": "cryptobot",
            "status": "paid",
            "invoice_id": invoice_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        data = load_data(DATA_FILE)
        data.append(purchase_data)
        save_data(DATA_FILE, data)
        
        # Удаляем из ожидающих
        pending_data.pop(order_index)
        save_data(PENDING_FILE, pending_data)
        
        text = (
            f"✅ Оплата подтверждена!\n\n"
            f"⚙ Версия: <b>{version}</b>\n"
            f"📦 Тариф: <b>{PERIOD_NAMES.get(plan, plan)}</b>\n"
            f"💲 Цена: <b>${price}</b>\n"
            f"🔑 Ваш ключ: <code>{key}</code>\n\n"
            f"Ссылка на группу с софтом:\n{SOFTWARE_GROUP_LINK}\n\n"
            f"⚠️ Сохраните ключ в надежном месте!"
        )
        edit_telegram_message(chat_id, message_id, text)
        answer_callback_query(callback_query_id, "✅ Оплата подтверждена!")
    elif status == 'active':
        answer_callback_query(callback_query_id, "⏳ Оплата еще не поступила")
    else:
        answer_callback_query(callback_query_id, f"❌ Статус платежа: {status}")

def handle_echo(chat_id, text):
    send_telegram_message(chat_id, f"🤖 Вы написали: {text}\n\nИспользуйте /start для начала работы")

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
            callback_query_id = callback["id"]
            
            # Основное меню
            if data == "menu_buy":
                handle_menu_buy(chat_id, message_id)
                answer_callback_query(callback_query_id)
            elif data == "menu_profile":
                handle_menu_profile(chat_id, message_id, user_id)
                answer_callback_query(callback_query_id)
            elif data == "menu_ref":
                handle_menu_ref(chat_id, message_id, user_id)
                answer_callback_query(callback_query_id)
            elif data == "back_main":
                handle_back_main(chat_id, message_id)
                answer_callback_query(callback_query_id)
            
            # Выбор версии
            elif data.startswith("ver_"):
                version = data.replace("ver_", "")
                handle_select_version(chat_id, message_id, version)
                answer_callback_query(callback_query_id)
            
            # Выбор тарифа
            elif data.startswith("plan_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    version = parts[1]
                    plan = parts[2]
                    price = parts[3]
                    handle_select_plan(chat_id, message_id, version, plan, price)
                    answer_callback_query(callback_query_id)
            
            # Выбор способа оплаты - Crypto
            elif data.startswith("pay_crypto_"):
                parts = data.split("_")
                if len(parts) >= 5:
                    version = parts[2]
                    plan = parts[3]
                    price = parts[4]
                    handle_pay_crypto(chat_id, message_id, version, plan, price)
                    answer_callback_query(callback_query_id)
            
            # Выбор способа оплаты - Рубли
            elif data.startswith("pay_rub_"):
                parts = data.split("_")
                if len(parts) >= 5:
                    version = parts[2]
                    plan = parts[3]
                    price = parts[4]
                    handle_pay_rub(chat_id, message_id, version, plan, price)
                    answer_callback_query(callback_query_id)
            
            # Проверка оплаты
            elif data.startswith("check_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    version = parts[1]
                    plan = parts[2]
                    price = parts[3]
                    answer_callback_query(callback_query_id, "🔍 Проверяем оплату...")
                    handle_check_payment(chat_id, message_id, version, plan, price, callback_query_id)
                else:
                    answer_callback_query(callback_query_id, "❌ Ошибка в данных заказа")
            
            # Смена языка
            elif data == "menu_lang_en":
                edit_telegram_message(chat_id, message_id, "✅ Language changed to English", back_button_markup())
                answer_callback_query(callback_query_id)
            
            else:
                answer_callback_query(callback_query_id)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "✅ NFT Tracker Bot is running via Webhook"

# ========== Запуск ==========
if __name__ == "__main__":
    print("🚀 Запуск бота с обновленными ценами и выбором оплаты...")
    
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
