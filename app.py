import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ---------------- WEB ----------------

@app.route("/")
def home():
    return "Kaif Shaurma bot is running!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ---------------- ДАННЫЕ ----------------

carts = {}
order_states = {}

SAUCES = [
    "Грибной",
    "Барбекю",
    "Бургер",
    "Горчичный",
    "Кисло-сладкий",
    "Сырный",
    "Томатный",
    "Фирменный для шаурмы",
    "Чесночный",
    "Шрирача",
    "Фирменный для шашлыка",
]

ADDITIONS = [
    "Ананас",
    "Зелень с луком",
    "Лук хрустящий",
    "Маринованные огурцы",
    "Морковь по-корейски",
    "Оливки",
    "Сыр твёрдый",
    "Фри",
    "Халапеньо",
]

MENU = {
    "shawarma_chicken": [
        ("Огненно-острая с курицей, 320 г", 380),
        ("Шаурма с курицей мини, 200 г", 250),
        ("Шаурма с курицей стандарт, 320 г", 315),
        ("Шаурма студенческая с курицей, 320 г", 250),
        ("Шаурма с курицей большая, 430 г", 370),
    ],
    "shawarma_pork": [
        ("Огненно-острая со свининой, 320 г", 420),
        ("Шаурма со свининой мини, 200 г", 285),
        ("Шаурма со свининой стандарт, 320 г", 350),
        ("Шаурма студенческая со свининой, 320 г", 280),
        ("Шаурма со свининой большая, 420 г", 395),
    ],
    "shawarma_vegan": [
        ("Шаурма веган мини, 200 г", 270),
        ("Шаурма веган стандарт, 320 г", 320),
        ("Шаурма веган большая, 430 г", 370),
    ],
    "doner": [
        ("Донер с курицей", 390),
        ("Донер со свининой", 410),
    ],
    "lulya": [
        ("Люля в лаваше — говядина, 200 г", 420),
        ("Люля в лаваше — курица, 200 г", 390),
    ],
    "sandwich": [
        ("Сэндвич с курицей, 200 г", 265),
        ("Сэндвич со свининой, 200 г", 275),
    ],
    "burger": [
        ("Гамбургер с говядиной", 440),
        ("Чикен-бургер", 400),
    ],
    "shashlik": [
        ("Шашлык из курицы, 200 г", 395),
        ("Шашлык из курицы, 300 г", 505),
        ("Шашлык из свинины, 200 г", 445),
        ("Шашлык из свинины, 300 г", 555),
    ],
}


# ---------------- КЛАВИАТУРЫ ----------------

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        types.KeyboardButton("🌯 Меню"),
        types.KeyboardButton("🛒 Корзина")
    )

    kb.row(
        types.KeyboardButton("➕ Добавки"),
        types.KeyboardButton("📍 Адрес")
    )

    kb.row(
        types.KeyboardButton("☎️ Связаться"),
        types.KeyboardButton("🔒 Конфиденциальность")
    )

    return kb


def menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        types.KeyboardButton("🌯 Шаурма"),
        types.KeyboardButton("🥙 Донеры")
    )

    kb.row(
        types.KeyboardButton("🍱 Комбо-наборы"),
        types.KeyboardButton("🍢 Шашлык")
    )

    kb.row(
        types.KeyboardButton("🥩 Люля в лаваше"),
        types.KeyboardButton("🍟 Снэки")
    )

    kb.row(
        types.KeyboardButton("🥪 Сэндвичи"),
        types.KeyboardButton("🍔 Бургеры")
    )

    kb.row(types.KeyboardButton("⬅️ Главное меню"))

    return kb


def shawarma_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        types.KeyboardButton("🐔 Шаурма с курицей"),
        types.KeyboardButton("🐷 Шаурма со свининой")
    )

    kb.row(types.KeyboardButton("🌱 Шаурма веган"))
    kb.row(types.KeyboardButton("⬅️ Назад в меню"))

    return kb


# ---------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------------

def get_cart(user_id):
    if user_id not in carts:
        carts[user_id] = []
    return carts[user_id]


def cart_total(user_id):
    return sum(item["price"] for item in get_cart(user_id))


def add_to_cart(user_id, name, price, details=None):
    item = {
        "name": name,
        "price": price,
        "details": details or []
    }

    get_cart(user_id).append(item)


def format_cart(user_id):
    cart = get_cart(user_id)

    if not cart:
        return "🛒 Ваша корзина пока пустая."

    text = "🛒 Ваша корзина:\n\n"

    for index, item in enumerate(cart, 1):
        text += f"{index}. {item['name']} — {item['price']} ₽\n"

        for detail in item["details"]:
            text += f"   • {detail}\n"

    text += f"\n💰 Итого: {cart_total(user_id)} ₽"

    return text


def send_category(chat_id, category):
    kb = types.InlineKeyboardMarkup()

    for index, (name, price) in enumerate(MENU[category]):
        kb.add(
            types.InlineKeyboardButton(
                f"{name} — {price} ₽",
                callback_data=f"item|{category}|{index}"
            )
        )

    bot.send_message(
        chat_id,
        "Выберите позицию 👇",
        reply_markup=kb
    )


# ---------------- START ----------------

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🌯 Добро пожаловать в «Кайф Шаурма»!\n\n"
        "Здесь можно посмотреть меню и оформить заказ.\n\n"
        "📍 Сейчас бот принимает заказы только на САМОВЫВОЗ.\n"
        "💳 Онлайн-оплаты пока нет — оплата при получении.",
        reply_markup=main_keyboard()
    )


# ---------------- ГЛАВНОЕ МЕНЮ ----------------

@bot.message_handler(func=lambda m: m.text == "🌯 Меню")
def show_menu(message):
    bot.send_message(
        message.chat.id,
        "Что хотите заказать? 👇",
        reply_markup=menu_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "⬅️ Главное меню")
def main_back(message):
    bot.send_message(
        message.chat.id,
        "Главное меню 👇",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "⬅️ Назад в меню")
def menu_back(message):
    show_menu(message)


# ---------------- ШАУРМА ----------------

@bot.message_handler(func=lambda m: m.text == "🌯 Шаурма")
def shawarma(message):
    bot.send_message(
        message.chat.id,
        "Выберите вид шаурмы 👇",
        reply_markup=shawarma_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "🐔 Шаурма с курицей")
def shawarma_chicken(message):
    send_category(message.chat.id, "shawarma_chicken")


@bot.message_handler(func=lambda m: m.text == "🐷 Шаурма со свининой")
def shawarma_pork(message):
    send_category(message.chat.id, "shawarma_pork")


@bot.message_handler(func=lambda m: m.text == "🌱 Шаурма веган")
def shawarma_vegan(message):
    send_category(message.chat.id, "shawarma_vegan")


# ---------------- ОСТАЛЬНЫЕ КАТЕГОРИИ ----------------

@bot.message_handler(func=lambda m: m.text == "🥙 Донеры")
def doner(message):
    send_category(message.chat.id, "doner")


@bot.message_handler(func=lambda m: m.text == "🥩 Люля в лаваше")
def lulya(message):
    send_category(message.chat.id, "lulya")


@bot.message_handler(func=lambda m: m.text == "🥪 Сэндвичи")
def sandwich(message):
    send_category(message.chat.id, "sandwich")


@bot.message_handler(func=lambda m: m.text == "🍔 Бургеры")
def burgers(message):
    send_category(message.chat.id, "burger")


@bot.message_handler(func=lambda m: m.text == "🍢 Шашлык")
def shashlik(message):
    send_category(message.chat.id, "shashlik")


# ---------------- ОБЫЧНЫЕ ПОЗИЦИИ ----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("item|"))
def choose_item(call):
    _, category, index = call.data.split("|")
    index = int(index)

    name, price = MENU[category][index]

    # Для шаурмы после выбора предлагаем добавки
    if category.startswith("shawarma"):
        order_states[call.from_user.id] = {
            "type": "shawarma",
            "name": name,
            "price": price,
            "details": []
        }

        show_shawarma_extras(call.message.chat.id)

    else:
        add_to_cart(
            call.from_user.id,
            name,
            price
        )

        bot.answer_callback_query(
            call.id,
            "Добавлено в корзину ✅"
        )

        bot.send_message(
            call.message.chat.id,
            f"✅ {name} добавлено в корзину.\n\n"
            f"💰 {price} ₽"
        )


# ---------------- ДОБАВКИ К ШАУРМЕ ----------------

def show_shawarma_extras(chat_id):
    kb = types.InlineKeyboardMarkup()

    for index, addition in enumerate(ADDITIONS):
        kb.add(
            types.InlineKeyboardButton(
                f"➕ {addition} +60 ₽",
                callback_data=f"shaw_add|{index}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "🥫 Добавить соус +60 ₽",
            callback_data="shaw_sauce"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "✅ Готово",
            callback_data="shaw_done"
        )
    )

    bot.send_message(
        chat_id,
        "Хотите добавить что-нибудь в шаурму?\n\n"
        "Можно выбрать несколько добавок.",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("shaw_add|"))
def shawarma_addition(call):
    user_id = call.from_user.id

    if user_id not in order_states:
        return

    index = int(call.data.split("|")[1])
    addition = ADDITIONS[index]

    order_states[user_id]["price"] += 60
    order_states[user_id]["details"].append(
        f"Добавка: {addition} (+60 ₽)"
    )

    bot.answer_callback_query(
        call.id,
        f"{addition} добавлено ✅"
    )


@bot.callback_query_handler(func=lambda call: call.data == "shaw_sauce")
def shawarma_sauce(call):
    kb = types.InlineKeyboardMarkup()

    for index, sauce in enumerate(SAUCES):
        kb.add(
            types.InlineKeyboardButton(
                f"{sauce} +60 ₽",
                callback_data=f"shaw_sauce_select|{index}"
            )
        )

    bot.send_message(
        call.message.chat.id,
        "Выберите дополнительный соус:",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("shaw_sauce_select|")
)
def shawarma_sauce_select(call):
    user_id = call.from_user.id
    index = int(call.data.split("|")[1])

    sauce = SAUCES[index]

    if user_id not in order_states:
        return

    order_states[user_id]["price"] += 60
    order_states[user_id]["details"].append(
        f"Соус: {sauce} (+60 ₽)"
    )

    bot.answer_callback_query(
        call.id,
        "Соус добавлен ✅"
    )


@bot.callback_query_handler(func=lambda call: call.data == "shaw_done")
def shawarma_done(call):
    user_id = call.from_user.id

    if user_id not in order_states:
        return

    item = order_states.pop(user_id)

    add_to_cart(
        user_id,
        item["name"],
        item["price"],
        item["details"]
    )

    bot.send_message(
        call.message.chat.id,
        f"✅ Шаурма добавлена в корзину.\n"
        f"Стоимость: {item['price']} ₽"
    )


# ---------------- КОМБО ----------------

@bot.message_handler(func=lambda m: m.text == "🍱 Комбо-наборы")
def combo(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "Комбо №1 — 420 ₽",
            callback_data="combo1"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Комбо №2 — 470 ₽",
            callback_data="combo2"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Комбо №3 — 520 ₽",
            callback_data="combo3"
        )
    )

    bot.send_message(
        message.chat.id,
        "🍱 Комбо-наборы:\n\n"
        "1️⃣ Шаурма с курицей стандарт + кофе 200 мл — 420 ₽\n\n"
        "2️⃣ Шаурма с курицей стандарт + картофель фри 100 г + соус — 470 ₽\n\n"
        "3️⃣ Чикен-бургер + картофель фри 100 г + соус — 520 ₽",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "combo1")
def combo1(call):
    kb = types.InlineKeyboardMarkup()

    coffees = ["Американо 200 мл", "Капучино 200 мл", "Латте 200 мл"]

    for index, coffee in enumerate(coffees):
        kb.add(
            types.InlineKeyboardButton(
                coffee,
                callback_data=f"coffee|{index}"
            )
        )

    bot.send_message(
        call.message.chat.id,
        "☕ Выберите кофе к комбо:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("coffee|"))
def coffee_select(call):
    coffees = ["Американо 200 мл", "Капучино 200 мл", "Латте 200 мл"]

    index = int(call.data.split("|")[1])
    coffee = coffees[index]

    add_to_cart(
        call.from_user.id,
        "Комбо №1",
        420,
        [
            "Шаурма с курицей стандарт",
            coffee
        ]
    )

    bot.send_message(
        call.message.chat.id,
        f"✅ Комбо №1 добавлено.\n☕ Кофе: {coffee}"
    )


def show_free_sauces(chat_id, combo_number):
    kb = types.InlineKeyboardMarkup()

    for index, sauce in enumerate(SAUCES):
        kb.add(
            types.InlineKeyboardButton(
                sauce,
                callback_data=f"free_sauce|{combo_number}|{index}"
            )
        )

    bot.send_message(
        chat_id,
        "🥫 Выберите соус:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "combo2")
def combo2(call):
    show_free_sauces(call.message.chat.id, "combo2")


@bot.callback_query_handler(func=lambda call: call.data == "combo3")
def combo3(call):
    show_free_sauces(call.message.chat.id, "combo3")


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("free_sauce|")
)
def free_sauce_select(call):
    _, kind, index = call.data.split("|")
    sauce = SAUCES[int(index)]

    if kind == "combo2":
        add_to_cart(
            call.from_user.id,
            "Комбо №2",
            470,
            [
                "Шаурма с курицей стандарт",
                "Картофель фри 100 г",
                f"Соус: {sauce}"
            ]
        )

    elif kind == "combo3":
        add_to_cart(
            call.from_user.id,
            "Комбо №3",
            520,
            [
                "Чикен-бургер",
                "Картофель фри 100 г",
                f"Соус: {sauce}"
            ]
        )

    elif kind == "country200":
        add_to_cart(
            call.from_user.id,
            "Картофель по-деревенски 200 г + соус 30 г",
            270,
            [f"Соус: {sauce}"]
        )

    elif kind == "fries200":
        add_to_cart(
            call.from_user.id,
            "Картофель фри 200 г + соус 30 г",
            260,
            [f"Соус: {sauce}"]
        )

    elif kind == "cheese":
        add_to_cart(
            call.from_user.id,
            "Сырные палочки 6 шт.",
            335,
            [f"Соус: {sauce}"]
        )

    bot.send_message(
        call.message.chat.id,
        f"✅ Добавлено в корзину.\n🥫 Соус: {sauce}"
    )


# ---------------- СНЭКИ ----------------

@bot.message_handler(func=lambda m: m.text == "🍟 Снэки")
def snacks(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "Картофель по-деревенски 100 г — 190 ₽",
            callback_data="snack_country100"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Картофель по-деревенски 200 г + соус — 270 ₽",
            callback_data="snack_country200"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Картофель фри 100 г — 180 ₽",
            callback_data="snack_fries100"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Картофель фри 200 г + соус — 260 ₽",
            callback_data="snack_fries200"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Наггетсы 4 шт. + фри 100 г — 260 ₽",
            callback_data="snack_nuggets4"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Наггетсы 6 шт. — 260 ₽",
            callback_data="snack_nuggets6"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Сырные палочки 6 шт. + соус — 335 ₽",
            callback_data="snack_cheese"
        )
    )

    bot.send_message(
        message.chat.id,
        "🍟 Выберите снэк:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "snack_country100")
def snack_country100(call):
    add_to_cart(
        call.from_user.id,
        "Картофель по-деревенски 100 г",
        190
    )
    bot.send_message(call.message.chat.id, "✅ Добавлено в корзину.")


@bot.callback_query_handler(func=lambda call: call.data == "snack_country200")
def snack_country200(call):
    show_free_sauces(call.message.chat.id, "country200")


@bot.callback_query_handler(func=lambda call: call.data == "snack_fries100")
def snack_fries100(call):
    add_to_cart(
        call.from_user.id,
        "Картофель фри 100 г",
        180
    )
    bot.send_message(call.message.chat.id, "✅ Добавлено в корзину.")


@bot.callback_query_handler(func=lambda call: call.data == "snack_fries200")
def snack_fries200(call):
    show_free_sauces(call.message.chat.id, "fries200")


@bot.callback_query_handler(func=lambda call: call.data == "snack_nuggets4")
def snack_nuggets4(call):
    add_to_cart(
        call.from_user.id,
        "Наггетсы 4 шт. + картофель фри 100 г",
        260
    )
    bot.send_message(call.message.chat.id, "✅ Добавлено в корзину.")


@bot.callback_query_handler(func=lambda call: call.data == "snack_nuggets6")
def snack_nuggets6(call):
    add_to_cart(
        call.from_user.id,
        "Наггетсы 6 шт.",
        260
    )
    bot.send_message(call.message.chat.id, "✅ Добавлено в корзину.")


@bot.callback_query_handler(func=lambda call: call.data == "snack_cheese")
def snack_cheese(call):
    show_free_sauces(call.message.chat.id, "cheese")


# ---------------- ОТДЕЛЬНЫЙ РАЗДЕЛ ДОБАВКИ ----------------

@bot.message_handler(func=lambda m: m.text == "➕ Добавки")
def additions_menu(message):
    kb = types.InlineKeyboardMarkup()

    for index, addition in enumerate(ADDITIONS):
        kb.add(
            types.InlineKeyboardButton(
                f"{addition} — 60 ₽",
                callback_data=f"extra_add|{index}"
            )
        )

    for index, sauce in enumerate(SAUCES):
        kb.add(
            types.InlineKeyboardButton(
                f"🥫 {sauce} — 60 ₽",
                callback_data=f"extra_sauce|{index}"
            )
        )

    bot.send_message(
        message.chat.id,
        "➕ Добавки и соусы — по 60 ₽:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("extra_add|"))
def extra_add(call):
    index = int(call.data.split("|")[1])
    addition = ADDITIONS[index]

    add_to_cart(
        call.from_user.id,
        f"Добавка: {addition}",
        60
    )

    bot.answer_callback_query(call.id, "Добавлено ✅")


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("extra_sauce|")
)
def extra_sauce(call):
    index = int(call.data.split("|")[1])
    sauce = SAUCES[index]

    add_to_cart(
        call.from_user.id,
        f"Соус: {sauce}",
        60
    )

    bot.answer_callback_query(call.id, "Добавлено ✅")


# ---------------- КОРЗИНА ----------------

@bot.message_handler(func=lambda m: m.text == "🛒 Корзина")
def show_cart(message):
    user_id = message.chat.id

    if not get_cart(user_id):
        bot.send_message(
            user_id,
            "🛒 Ваша корзина пока пустая."
        )
        return

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "✅ Оформить заказ",
            callback_data="checkout"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🗑 Очистить корзину",
            callback_data="clear_cart"
        )
    )

    bot.send_message(
        user_id,
        format_cart(user_id),
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def clear_cart(call):
    carts[call.from_user.id] = []

    bot.send_message(
        call.message.chat.id,
        "🗑 Корзина очищена."
    )


# ---------------- ОФОРМЛЕНИЕ ----------------

@bot.callback_query_handler(func=lambda call: call.data == "checkout")
def checkout(call):
    user_id = call.from_user.id

    if not get_cart(user_id):
        bot.send_message(
            call.message.chat.id,
            "Корзина пустая."
        )
        return

    order_states[user_id] = {
        "checkout": True
    }

    msg = bot.send_message(
        call.message.chat.id,
        "👤 Как вас зовут?"
    )

    bot.register_next_step_handler(msg, get_customer_name)


def get_customer_name(message):
    user_id = message.chat.id

    order_states[user_id]["name"] = message.text

    msg = bot.send_message(
        user_id,
        "☎️ Напишите номер телефона для связи:"
    )

    bot.register_next_step_handler(msg, get_customer_phone)


def get_customer_phone(message):
    user_id = message.chat.id

    order_states[user_id]["phone"] = message.text

    msg = bot.send_message(
        user_id,
        "⏰ Через сколько вы подойдёте за заказом?\n\n"
        "Например: через 20 минут или в 21:30."
    )

    bot.register_next_step_handler(msg, get_pickup_time)


def get_pickup_time(message):
    user_id = message.chat.id

    order_states[user_id]["pickup"] = message.text

    data = order_states[user_id]

    text = (
        "Проверьте заказ 👇\n\n"
        f"{format_cart(user_id)}\n\n"
        f"👤 Имя: {data['name']}\n"
        f"☎️ Телефон: {data['phone']}\n"
        f"⏰ Самовывоз: {data['pickup']}\n\n"
        "Нажимая «Подтвердить заказ», вы соглашаетесь "
        "с обработкой данных для выполнения заказа."
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить заказ",
            callback_data="confirm_order"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "❌ Отменить",
            callback_data="cancel_order"
        )
    )

    bot.send_message(
        user_id,
        text,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_order")
def confirm_order(call):
    user_id = call.from_user.id

    if user_id not in order_states:
        return

    data = order_states[user_id]

    admin_text = (
        "🔥 НОВЫЙ ЗАКАЗ — КАЙФ ШАУРМА\n\n"
        f"{format_cart(user_id)}\n\n"
        f"👤 Имя: {data.get('name')}\n"
        f"☎️ Телефон: {data.get('phone')}\n"
        f"⏰ Подойдёт: {data.get('pickup')}\n"
        f"🆔 Telegram ID: {user_id}\n\n"
        "📍 Самовывоз"
    )

    if ADMIN_CHAT_ID:
        try:
            bot.send_message(
                int(ADMIN_CHAT_ID),
                admin_text
            )
        except Exception as error:
            print("Ошибка отправки админу:", error)

    bot.edit_message_text(
        "✅ Заказ принят!\n\n"
        "Спасибо за заказ ❤️\n"
        "Мы получили вашу заявку.\n\n"
        f"💰 Сумма: {cart_total(user_id)} ₽\n"
        f"⏰ Самовывоз: {data.get('pickup')}\n\n"
        "Оплата производится при получении.",
        call.message.chat.id,
        call.message.message_id
    )

    carts[user_id] = []
    order_states.pop(user_id, None)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_order")
def cancel_order(call):
    order_states.pop(call.from_user.id, None)

    bot.edit_message_text(
        "❌ Оформление заказа отменено.\n"
        "Товары остались в корзине.",
        call.message.chat.id,
        call.message.message_id
    )


# ---------------- ИНФОРМАЦИЯ ----------------

@bot.message_handler(func=lambda m: m.text == "📍 Адрес")
def address(message):
    bot.send_message(
        message.chat.id,
        "📍 Здесь укажем точный адрес «Кайф Шаурма»."
    )


@bot.message_handler(func=lambda m: m.text == "☎️ Связаться")
def contact(message):
    bot.send_message(
        message.chat.id,
        "☎️ Здесь укажем номер телефона или Telegram для связи."
    )


@bot.message_handler(func=lambda m: m.text == "🔒 Конфиденциальность")
def privacy(message):
    bot.send_message(
        message.chat.id,
        "🔒 Политика конфиденциальности\n\n"
        "Для оформления заказа бот может запросить ваше имя, "
        "номер телефона, состав заказа и желаемое время самовывоза.\n\n"
        "Эти данные используются только для обработки и выполнения заказа "
        "и не предназначены для рекламной рассылки.\n\n"
        "Продолжая оформление заказа, вы соглашаетесь на обработку "
        "предоставленных данных в целях выполнения вашего заказа."
    )


# ---------------- ПРОЧИЕ СООБЩЕНИЯ ----------------

@bot.message_handler(func=lambda message: True)
def other_messages(message):
    bot.send_message(
        message.chat.id,
        "Выберите нужный раздел 👇",
        reply_markup=main_keyboard()
    )


# ---------------- ЗАПУСК ----------------

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
