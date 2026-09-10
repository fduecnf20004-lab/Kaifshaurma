import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


@app.route("/")
def home():
    return "Kaif Shaurma bot is running!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row(
        types.KeyboardButton("🌯 Меню"),
        types.KeyboardButton("🛒 Сделать заказ")
    )

    keyboard.row(
        types.KeyboardButton("📍 Адрес"),
        types.KeyboardButton("☎️ Связаться")
    )

    return keyboard


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🌯 Добро пожаловать в «Кайф Шаурма»!\n\n"
        "Здесь можно посмотреть меню и оформить заказ.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🌯 Меню")
def show_menu(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row(
        types.KeyboardButton("🌯 Шаурма"),
        types.KeyboardButton("🥙 Донеры")
    )

    keyboard.row(
        types.KeyboardButton("🍢 Шашлык"),
        types.KeyboardButton("🥩 Люля")
    )

    keyboard.row(
        types.KeyboardButton("🍟 Снеки"),
        types.KeyboardButton("🥪 Сэндвичи")
    )

    keyboard.row(
        types.KeyboardButton("🍱 Комбо-наборы"),
        types.KeyboardButton("🥫 Соусы")
    )

    keyboard.row(
        types.KeyboardButton("⬅️ Назад")
    )

    bot.send_message(
        message.chat.id,
        "Выберите категорию:",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text == "🌯 Шаурма")
def shawarma(message):
    bot.send_message(
        message.chat.id,
        "🌯 Шаурма:\n\n"
        "• С курицей\n"
        "• Со свининой\n"
        "• Веган\n\n"
        "Цены добавим по вашему меню."
    )


@bot.message_handler(func=lambda message: message.text == "🥙 Донеры")
def doner(message):
    bot.send_message(
        message.chat.id,
        "🥙 Донеры\n\n"
        "Здесь добавим названия и цены из меню."
    )


@bot.message_handler(func=lambda message: message.text == "🍢 Шашлык")
def shashlik(message):
    bot.send_message(
        message.chat.id,
        "🍢 Шашлык\n\n"
        "Здесь добавим виды шашлыка и цены."
    )


@bot.message_handler(func=lambda message: message.text == "🥩 Люля")
def lulya(message):
    bot.send_message(
        message.chat.id,
        "🥩 Люля\n\n"
        "Здесь добавим варианты люля и цены."
    )


@bot.message_handler(func=lambda message: message.text == "🍟 Снеки")
def snacks(message):
    bot.send_message(
        message.chat.id,
        "🍟 Снеки\n\n"
        "Картофель фри, наггетсы, сырные палочки и другое."
    )


@bot.message_handler(func=lambda message: message.text == "🥪 Сэндвичи")
def sandwiches(message):
    bot.send_message(
        message.chat.id,
        "🥪 Сэндвичи\n\n"
        "Здесь добавим ассортимент и цены."
    )


@bot.message_handler(func=lambda message: message.text == "🍱 Комбо-наборы")
def combo(message):
    bot.send_message(
        message.chat.id,
        "🍱 Комбо-наборы\n\n"
        "Здесь добавим ваши комбо."
    )


@bot.message_handler(func=lambda message: message.text == "🥫 Соусы")
def sauces(message):
    bot.send_message(
        message.chat.id,
        "🥫 Соусы\n\n"
        "Здесь добавим виды соусов и цены."
    )


@bot.message_handler(func=lambda message: message.text == "⬅️ Назад")
def back(message):
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=main_keyboard()
    )


orders = {}


@bot.message_handler(func=lambda message: message.text == "🛒 Сделать заказ")
def make_order(message):
    orders[message.chat.id] = {}

    msg = bot.send_message(
        message.chat.id,
        "Напишите, что хотите заказать.\n\n"
        "Например: 2 шаурмы с курицей и картофель фри."
    )

    bot.register_next_step_handler(msg, get_order)


def get_order(message):
    orders[message.chat.id]["order"] = message.text

    msg = bot.send_message(
        message.chat.id,
        "Как вас зовут?"
    )

    bot.register_next_step_handler(msg, get_name)


def get_name(message):
    orders[message.chat.id]["name"] = message.text

    msg = bot.send_message(
        message.chat.id,
        "Напишите номер телефона для связи:"
    )

    bot.register_next_step_handler(msg, get_phone)


def get_phone(message):
    user_id = message.chat.id
    orders[user_id]["phone"] = message.text

    order = orders[user_id]

    text = (
        "Проверьте заказ:\n\n"
        f"🛒 Заказ: {order['order']}\n"
        f"👤 Имя: {order['name']}\n"
        f"☎️ Телефон: {order['phone']}\n\n"
        "Если всё правильно — подтвердите заказ."
    )

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить заказ",
            callback_data="confirm_order"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "❌ Отменить",
            callback_data="cancel_order"
        )
    )

    bot.send_message(
        user_id,
        text,
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_order")
def confirm_order(call):
    bot.edit_message_text(
        "✅ Заказ принят!\n\n"
        "Спасибо! Скоро с вами свяжутся.",
        call.message.chat.id,
        call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == "cancel_order")
def cancel_order(call):
    orders.pop(call.message.chat.id, None)

    bot.edit_message_text(
        "❌ Заказ отменён.",
        call.message.chat.id,
        call.message.message_id
    )


@bot.message_handler(func=lambda message: message.text == "📍 Адрес")
def address(message):
    bot.send_message(
        message.chat.id,
        "📍 Здесь укажем адрес «Кайф Шаурма»."
    )


@bot.message_handler(func=lambda message: message.text == "☎️ Связаться")
def contact(message):
    bot.send_message(
        message.chat.id,
        "☎️ Здесь укажем номер телефона."
    )


@bot.message_handler(func=lambda message: True)
def other_messages(message):
    bot.send_message(
        message.chat.id,
        "Выберите нужный раздел 👇",
        reply_markup=main_keyboard()
    )


if __name__ == "__main__":
    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    print("Бот запущен")

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60
    )
