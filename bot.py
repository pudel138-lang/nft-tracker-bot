# bot.py
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
BOT_TOKEN = "8269202056:AAEsbpsM93ey7C0Zh9dlT6oUKW2a_rFWl5w"
CRYPTOPAY_TOKEN = "480624:AAumVGyvHpmnmTKE5SB71VqMnT7EESjojse"
NGROK_BASE = "https://malissa-unsupporting-else.ngrok-free.dev"

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

# ========== Aiogram + Flask ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = Flask(__name__)

# основной event loop для aiogram (используем его в webhook)
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

# ========== Хэндлеры aiogram ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # показываем меню сразу
    await message.answer("NFT TRACKER", reply_markup=main_menu_markup())

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"Your chat_id = {message.from_user.id}")

# Используем F.data фильтры вместо lambda
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

# версии — safe photo send через FSInputFile
@dp.callback_query(F.data.startswith("ver_"))
async def cb_version(callback: types.CallbackQuery):
    v = callback.data.split("_", 1)[1]
    title = v.capitalize()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    if v == "LITE":
        desc = "LITE — упрощённая версия софта, содержит только ключевые функции."
        img_path = os.path.join(base_dir, IMG_LITE)
    elif v == "VIP":
        desc = "VIP — полная версия софта с расширенным функционалом."
        img_path = os.path.join(base_dir, IMG_VIP)
    else:
        desc = "Android Termux — скрипт на Android, работает через Termux."
        img_path = os.path.join(base_dir, IMG_TERMUX)

    caption = (
        f"<b>💼 NFT TRACKER — {quote_html(title)}</b>\n\n"
        f"{quote_html(desc)}\n\n"
        f"<b>💰 Тарифы:</b>"
    )

    try:
        if os.path.exists(img_path):
            size_mb = os.path.getsize(img_path) / (1024 * 1024)
            logger.info("Файл %s найден (%.2f MB)", img_path, size_mb)

            # safety: если очень большой, не швыряем в chat как фото
            if size_mb > 40:
                await callback.message.answer(
                    f"⚠️ Изображение слишком большое ({size_mb:.2f} MB). Отправляю текстовую версию.",
                    reply_markup=plan_markup(v)
                )
                await callback.message.edit_text(caption, parse_mode="HTML", reply_markup=plan_markup(v))
                return

            photo = FSInputFile(img_path)
            await callback.message.answer_photo(
                photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=plan_markup(v)
            )
            await asyncio.sleep(0.35)
            try:
                await callback.message.delete()
            except Exception:
                pass
        else:
            logger.info("Картинка не найдена: %s", img_path)
            await callback.message.edit_text(caption, parse_mode="HTML", reply_markup=plan_markup(v))

    except Exception as e:
        logger.exception("Ошибка при отправке картинки: %s", e)
        await callback.message.answer(
            f"⚠️ Не удалось отправить картинку.\nОшибка: <code>{quote_html(str(e))}</code>",
            parse_mode="HTML",
            reply_markup=plan_markup(v)
        )

# Заказы — проверяем callback начинающийся с order|
@dp.callback_query(F.data.startswith("order|"))
async def cb_order(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("|")
        _, version, plan, price = parts
    except Exception:
        await callback.answer("Ошибка данных заказа", show_alert=True)
        return

    user_id = callback.from_user.id
    price = float(price)

    await callback.answer("Создаю счёт... Подожди", show_alert=False)

    payload_obj = {"user_id": user_id, "version": version, "plan": plan}
    async with aiohttp.ClientSession() as session:
        url = "https://pay.crypt.bot/api/createInvoice"
        headers = {"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN}
        body = {
            "asset": DEFAULT_ASSET,
            "amount": str(price),
            "description": f"Покупка {version} {plan} ({user_id})",
            "hidden_message": "Спасибо за покупку!",
            "payload": json.dumps(payload_obj),
            "allow_comments": False,
            "allow_anonymous": False
        }
        try:
            async with session.post(url, headers=headers, json=body) as resp:
                data = await resp.json()
        except Exception as e:
            logger.exception("Ошибка создания инвойса: %s", e)
            await callback.message.answer("❌ Ошибка при создании счёта. Попробуй позже.")
            return

    if not data.get("ok"):
        await callback.message.answer(f"❌ Ошибка от CryptoPay: {data}")
        return

    invoice = data["result"]
    invoice_id = invoice.get("invoice_id")
    pay_url = invoice.get("pay_url")
    asset = invoice.get("asset") if "asset" in invoice else DEFAULT_ASSET

    pending_invoices[str(invoice_id)] = {
        "user_id": user_id,
        "version": version,
        "plan": plan,
        "price": price,
        "asset": asset,
        "created_at": datetime.utcnow().isoformat(),
    }

    await callback.message.answer(
        f"💸 Счёт создан: {pretty_price(price)} ({asset})\nОплатите по ссылке:\n{pay_url}\n\nПосле оплаты я пришлю ключ автоматически."
    )

# ========== Flask webhook от CryptoPay ==========
@app.route("/cryptopay/webhook", methods=["POST"])
def cryptopay_webhook():
    data = request.get_json(force=True)
    logger.info("Webhook получен: %s", data)

    try:
        if data.get("update_type") == "invoice_paid":
            payload_raw = data.get("payload") or data.get("update", {}).get("payload")
            invoice_obj = data.get("invoice") or data.get("update", {})

            payload = None
            try:
                if isinstance(payload_raw, str) and payload_raw.startswith("{"):
                    payload = json.loads(payload_raw)
                else:
                    payload = payload_raw
            except Exception:
                payload = payload_raw

            if isinstance(payload, dict):
                user_id = int(payload.get("user_id")) if payload.get("user_id") else None
                version = payload.get("version")
                plan = payload.get("plan")
            else:
                user_id = int(payload) if payload else None
                version = None
                plan = None

            invoice_id = str(invoice_obj.get("invoice_id") or data.get("invoice_id") or invoice_obj.get("id"))

            order = pending_invoices.get(invoice_id)
            if order:
                if not user_id:
                    user_id = order.get("user_id")
                if not version:
                    version = order.get("version")
                if not plan:
                    plan = order.get("plan")
                price = order.get("price")
                asset = order.get("asset", DEFAULT_ASSET)
            else:
                price = invoice_obj.get("amount") or invoice_obj.get("price") or None
                asset = invoice_obj.get("asset") or DEFAULT_ASSET

            key = gen_key(version or "KEY")
            record = {
                "invoice_id": invoice_id,
                "user_id": int(user_id) if user_id else None,
                "version": version,
                "plan": plan,
                "price": price,
                "asset": asset,
                "key": key,
                "created_at": datetime.utcnow().isoformat()
            }
            append_purchase(record)

            if invoice_id in pending_invoices:
                del pending_invoices[invoice_id]

            if user_id:
                asyncio.run_coroutine_threadsafe(
                    send_payment_success(int(user_id), version, plan, key, price, asset),
                    main_loop
                )
            else:
                logger.warning("Не удалось определить user_id для invoice %s", invoice_id)

        return "ok", 200

    except Exception as e:
        logger.exception("Ошибка обработки webhook: %s", e)
        return "error", 400

# ========== Отправка сообщения о платеже ==========
async def send_payment_success(user_id, version, plan, key, price, asset):
    try:
        txt = (
            f"✅ Оплата получена!\n\n"
            f"🔑 Ваш ключ: <code>{quote_html(key)}</code>\n"
            f"📦 Версия: {quote_html(version)}</code>\n"
            f"📄 План: {quote_html(plan)}</code>\n"
            f"💲 Цена: {quote_html(price)} {quote_html(asset)}</code>\n\n"
            f"Скачать/получить файл и инструкции можно в группе:\n{SOFTWARE_GROUP_LINK}"
        )
        await bot.send_message(chat_id=int(user_id), text=txt, parse_mode="HTML")
    except Exception as e:
        logger.exception("Ошибка при отправке сообщения пользователю %s: %s", user_id, e)

# ========== Запуск Flask + Aiogram ==========
def start_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    main_loop.run_until_complete(dp.start_polling(bot))
