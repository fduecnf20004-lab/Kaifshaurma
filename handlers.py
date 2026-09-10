import logging 
from datetime import datetime
from typing import Any
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import (
    ADDRESS,
    ADMIN_IDS,
    BUSINESS_NAME,
    CONTACT,
    KITCHEN_IDS,
)
from keyboards import (
    admin_keyboard,
    cart_keyboard,
    categories_keyboard,
    coffee_keyboard,
    confirm_order_keyboard,
    extras_keyboard,
    main_menu_keyboard,
    products_keyboard,
    sauces_keyboard,
    shawarma_addons_keyboard,
    shawarma_options_keyboard,
    standalone_addons_keyboard,
    standalone_sauces_keyboard,
    subcategories_keyboard,
)
from storage import storage
from utils import (
    add_to_cart,
    cart_total,
    clear_cart,
    find_addon,
    find_category,
    find_coffee,
    find_product,
    find_sauce,
    find_subcategory,
    format_cart,
    format_product_card,
    format_product_name,
    get_cart,
    get_menu,
    is_admin,
    is_staff,
)


router = Router()


class ShawarmaState(StatesGroup):
    configuring = State()


class CheckoutState(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_pickup = State()
    waiting_confirmation = State()


async def safe_answer_callback(
    callback: CallbackQuery,
    text: str | None = None,
    show_alert: bool = False,
) -> None:
    try:
        await callback.answer(
            text=text,
            show_alert=show_alert,
        )
    except TelegramBadRequest:
        pass


async def safe_edit(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if not callback.message:
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return

        logging.warning(
            "Не удалось изменить сообщение: %s",
            error,
        )

        try:
            await callback.message.answer(
                text,
                reply_markup=reply_markup,
            )
        except Exception:
            logging.exception(
                "Не удалось отправить сообщение"
            )


def kitchen_order_keyboard(
    order_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨‍🍳 Принять",
                    callback_data=f"kitchen:accept:{order_id}",
                ),
                InlineKeyboardButton(
                    text="✅ Готов",
                    callback_data=f"kitchen:ready:{order_id}",
                ),
            ]
        ]
    )


async def show_home(
    target: Message | CallbackQuery,
) -> None:
    user_id = target.from_user.id

    text = (
        f"🌯 *Добро пожаловать в «{BUSINESS_NAME}»!*\n\n"
        "Здесь можно собрать заказ на самовывоз.\n\n"
        "📍 Сейчас бот работает *только на самовывоз*.\n"
        "💳 Оплата — при получении."
    )

    keyboard = main_menu_keyboard(
        is_admin(user_id, ADMIN_IDS)
    )

    if isinstance(target, CallbackQuery):
        await safe_edit(
            target,
            text,
            keyboard,
        )
        await safe_answer_callback(target)
        return

    await target.answer(
        text,
        reply_markup=keyboard,
    )


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await show_home(message)


@router.message(Command("menu"))
async def menu_command(
    message: Message,
) -> None:
    await message.answer(
        "🌯 *Меню*\n\nВыберите категорию:",
        reply_markup=await categories_keyboard(),
    )


@router.message(Command("admin"))
async def admin_command(
    message: Message,
) -> None:
    if not is_admin(
        message.from_user.id,
        ADMIN_IDS,
    ):
        await message.answer(
            "⛔ Доступ запрещён."
        )
        return

    await message.answer(
        "⚙️ *Админ-панель*",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "home")
async def home_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await show_home(callback)


@router.callback_query(F.data == "menu")
async def menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await safe_edit(
        callback,
        "🌯 *Меню*\n\nВыберите категорию:",
        await categories_keyboard(),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data.startswith("category:")
)
async def category_callback(
    callback: CallbackQuery,
) -> None:
    category_id = callback.data.split(
        ":",
        1,
    )[1]

    category = await find_category(
        category_id
    )

    if not category:
        await safe_answer_callback(
            callback,
            "Категория не найдена",
            True,
        )
        return

    subcategories = category.get(
        "subcategories",
        [],
    )

    if subcategories:
        await safe_edit(
            callback,
            f"*{category['name']}*\n\nВыберите раздел:",
            await subcategories_keyboard(
                category_id
            ),
        )

        await safe_answer_callback(callback)
        return

    items = category.get(
        "items",
        [],
    )

    await safe_edit(
        callback,
        f"*{category['name']}*\n\nВыберите позицию:",
        products_keyboard(
            items,
            "menu",
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data.startswith("subcategory:")
)
async def subcategory_callback(
    callback: CallbackQuery,
) -> None:
    try:
        _, category_id, subcategory_id = (
            callback.data.split(":", 2)
        )
    except ValueError:
        await safe_answer_callback(
            callback,
            "Ошибка раздела",
            True,
        )
        return

    subcategory = await find_subcategory(
        category_id,
        subcategory_id,
    )

    if not subcategory:
        await safe_answer_callback(
            callback,
            "Раздел не найден",
            True,
        )
        return

    await safe_edit(
        callback,
        f"*{subcategory['name']}*\n\nВыберите позицию:",
        products_keyboard(
            subcategory.get(
                "items",
                [],
            ),
            f"category:{category_id}",
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data.startswith("product:")
)
async def product_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    product_id = callback.data.split(
        ":",
        1,
    )[1]

    product = await find_product(
        product_id
    )

    if not product:
        await safe_answer_callback(
            callback,
            "Товар не найден",
            True,
        )
        return

    if product.get("allow_extras"):
        await state.clear()

        await state.set_state(
            ShawarmaState.configuring
        )

        await state.update_data(
            product_id=product_id,
            selected_addons=[],
            selected_sauce=None,
        )

        await safe_edit(
            callback,
            (
                f"{format_product_card(product)}\n\n"
                "Можно выбрать добавки "
                "и дополнительный соус."
            ),
            await shawarma_options_keyboard(
                set(),
                None,
            ),
        )

        await safe_answer_callback(callback)
        return

    selection = product.get(
        "selection"
    )

    if selection:
        selection_type = selection.get(
            "type"
        )

        if selection_type == "coffee":
            await state.update_data(
                pending_product_id=product_id
            )

            await safe_edit(
                callback,
                (
                    f"{format_product_card(product)}\n\n"
                    "☕ *Выберите кофе:*"
                ),
                await coffee_keyboard(
                    product_id
                ),
            )

            await safe_answer_callback(callback)
            return

        if selection_type == "sauce":
            await state.update_data(
                pending_product_id=product_id
            )

            await safe_edit(
                callback,
                (
                    f"{format_product_card(product)}\n\n"
                    "🥫 *Выберите соус:*"
                ),
                await sauces_keyboard(
                    f"product_{product_id}"
                ),
            )

            await safe_answer_callback(callback)
            return

    add_to_cart(
        callback.from_user.id,
        {
            "product_id": product_id,
            "name": format_product_name(
                product
            ),
            "base_price": product["price"],
            "total_price": product["price"],
            "details": [],
        },
    )

    await safe_edit(
        callback,
        (
            "✅ *Добавлено в корзину*\n\n"
            f"{format_product_name(product)}\n"
            f"💰 {product['price']} ₽\n\n"
            f"🛒 В корзине на сумму: "
            f"*{cart_total(callback.from_user.id)} ₽*"
        ),
        main_menu_keyboard(
            is_admin(
                callback.from_user.id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(
        callback,
        "Добавлено ✅",
    )
@router.callback_query(
    ShawarmaState.configuring,
    F.data == "shawarma:addons",
)
async def shawarma_addons_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    selected_addons = set(
        data.get("selected_addons", [])
    )

    await safe_edit(
        callback,
        "➕ *Добавки*\n\n"
        "Нажмите на добавку, чтобы выбрать её.\n"
        "Повторное нажатие уберёт добавку.",
        await shawarma_addons_keyboard(
            selected_addons
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    ShawarmaState.configuring,
    F.data.startswith("shawarma:addon:")
)
async def shawarma_addon_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    addon_id = callback.data.split(
        ":",
        2,
    )[2]

    addon = await find_addon(
        addon_id
    )

    if not addon:
        await safe_answer_callback(
            callback,
            "Добавка не найдена",
            True,
        )
        return

    data = await state.get_data()

    selected_addons = set(
        data.get("selected_addons", [])
    )

    if addon_id in selected_addons:
        selected_addons.remove(
            addon_id
        )

        text = "Добавка убрана"
    else:
        selected_addons.add(
            addon_id
        )

        text = "Добавка выбрана"

    await state.update_data(
        selected_addons=list(
            selected_addons
        )
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=(
                await shawarma_addons_keyboard(
                    selected_addons
                )
            )
        )
    except TelegramBadRequest:
        pass

    await safe_answer_callback(
        callback,
        text,
    )


@router.callback_query(
    ShawarmaState.configuring,
    F.data == "shawarma:sauces",
)
async def shawarma_sauces_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    selected_sauce = data.get(
        "selected_sauce"
    )

    await safe_edit(
        callback,
        "🥫 *Дополнительный соус*\n\n"
        "Выберите один соус.\n"
        "Стоимость каждого — *60 ₽*.",
        await sauces_keyboard(
            "shawarma",
            selected_sauce,
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    ShawarmaState.configuring,
    F.data == "shawarma:options",
)
async def shawarma_options_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    product = await find_product(
        data.get(
            "product_id",
            "",
        )
    )

    if not product:
        await state.clear()

        await safe_answer_callback(
            callback,
            "Позиция не найдена",
            True,
        )
        return

    selected_addons = set(
        data.get("selected_addons", [])
    )

    selected_sauce = data.get(
        "selected_sauce"
    )

    sauce_name = "не выбран"

    if selected_sauce:
        sauce = await find_sauce(
            selected_sauce
        )

        if sauce:
            sauce_name = sauce["name"]

    await safe_edit(
        callback,
        (
            f"{format_product_card(product)}\n\n"
            f"➕ Добавок выбрано: "
            f"*{len(selected_addons)}*\n"
            f"🥫 Соус: *{sauce_name}*"
        ),
        await shawarma_options_keyboard(
            selected_addons,
            selected_sauce,
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data.startswith("sauce:")
)
async def sauce_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    try:
        _, target, sauce_id = (
            callback.data.split(
                ":",
                2,
            )
        )
    except ValueError:
        await safe_answer_callback(
            callback,
            "Ошибка выбора соуса",
            True,
        )
        return

    sauce = await find_sauce(
        sauce_id
    )

    if not sauce:
        await safe_answer_callback(
            callback,
            "Соус не найден",
            True,
        )
        return

    if target == "shawarma":
        data = await state.get_data()

        if not data.get("product_id"):
            await safe_answer_callback(
                callback,
                "Сначала выберите шаурму",
                True,
            )
            return

        await state.update_data(
            selected_sauce=sauce_id
        )

        selected_addons = set(
            data.get(
                "selected_addons",
                [],
            )
        )

        await safe_edit(
            callback,
            (
                "🥫 *Соус выбран*\n\n"
                f"{sauce['name']}\n"
                f"+{sauce['price']} ₽"
            ),
            await shawarma_options_keyboard(
                selected_addons,
                sauce_id,
            ),
        )

        await safe_answer_callback(
            callback,
            "Соус выбран ✅",
        )
        return

    if target.startswith(
        "product_"
    ):
        product_id = target.removeprefix(
            "product_"
        )

        product = await find_product(
            product_id
        )

        if not product:
            await safe_answer_callback(
                callback,
                "Товар не найден",
                True,
            )
            return

        add_to_cart(
            callback.from_user.id,
            {
                "product_id": product_id,
                "name": format_product_name(
                    product
                ),
                "base_price": product["price"],
                "total_price": product["price"],
                "details": [
                    f"Соус: {sauce['name']}"
                ],
            },
        )

        await state.clear()

        await safe_edit(
            callback,
            (
                "✅ *Добавлено в корзину*\n\n"
                f"{format_product_name(product)}\n"
                f"🥫 Соус: {sauce['name']}\n"
                f"💰 {product['price']} ₽\n\n"
                f"🛒 В корзине на сумму: "
                f"*{cart_total(callback.from_user.id)} ₽*"
            ),
            main_menu_keyboard(
                is_admin(
                    callback.from_user.id,
                    ADMIN_IDS,
                )
            ),
        )

        await safe_answer_callback(
            callback,
            "Добавлено ✅",
        )


@router.callback_query(
    ShawarmaState.configuring,
    F.data == "shawarma:done",
)
async def shawarma_done_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    product = await find_product(
        data.get(
            "product_id",
            "",
        )
    )

    if not product:
        await state.clear()

        await safe_answer_callback(
            callback,
            "Шаурма не найдена",
            True,
        )
        return

    menu = await get_menu()

    selected_addons = set(
        data.get("selected_addons", [])
    )

    details = []
    extras_total = 0

    for addon in menu.get(
        "addons",
        [],
    ):
        if addon["id"] not in selected_addons:
            continue

        addon_price = int(
            addon["price"]
        )

        extras_total += addon_price

        details.append(
            f"{addon['name']} "
            f"(+{addon_price} ₽)"
        )

    selected_sauce = data.get(
        "selected_sauce"
    )

    if selected_sauce:
        sauce = await find_sauce(
            selected_sauce
        )

        if sauce:
            sauce_price = int(
                sauce["price"]
            )

            extras_total += sauce_price

            details.append(
                f"Соус: {sauce['name']} "
                f"(+{sauce_price} ₽)"
            )

    total_price = (
        int(product["price"])
        + extras_total
    )

    add_to_cart(
        callback.from_user.id,
        {
            "product_id": product["id"],
            "name": format_product_name(
                product
            ),
            "base_price": product["price"],
            "total_price": total_price,
            "details": details,
        },
    )

    await state.clear()

    await safe_edit(
        callback,
        (
            "✅ *Шаурма добавлена в корзину*\n\n"
            f"{format_product_name(product)}\n"
            f"💰 С добавками: "
            f"*{total_price} ₽*\n\n"
            f"🛒 Общая сумма корзины: "
            f"*{cart_total(callback.from_user.id)} ₽*"
        ),
        main_menu_keyboard(
            is_admin(
                callback.from_user.id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(
        callback,
        "Добавлено ✅",
    )


@router.callback_query(
    F.data.startswith("coffee:")
)
async def coffee_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    try:
        _, product_id, coffee_id = (
            callback.data.split(
                ":",
                2,
            )
        )
    except ValueError:
        await safe_answer_callback(
            callback,
            "Ошибка выбора кофе",
            True,
        )
        return

    product = await find_product(
        product_id
    )

    coffee = await find_coffee(
        coffee_id
    )

    if not product or not coffee:
        await safe_answer_callback(
            callback,
            "Не удалось найти позицию",
            True,
        )
        return

    details = []

    if product.get("description"):
        details.append(
            product["description"]
        )

    details.append(
        f"Кофе: {coffee['name']} "
        f"{coffee['volume']}"
    )

    add_to_cart(
        callback.from_user.id,
        {
            "product_id": product_id,
            "name": product["name"],
            "base_price": product["price"],
            "total_price": product["price"],
            "details": details,
        },
    )

    await state.clear()

    await safe_edit(
        callback,
        (
            "✅ *Комбо добавлено в корзину*\n\n"
            f"{product['name']}\n"
            f"☕ {coffee['name']} "
            f"{coffee['volume']}\n"
            f"💰 {product['price']} ₽\n\n"
            f"🛒 Общая сумма: "
            f"*{cart_total(callback.from_user.id)} ₽*"
        ),
        main_menu_keyboard(
            is_admin(
                callback.from_user.id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(
        callback,
        "Добавлено ✅",
    )


@router.callback_query(
    F.data == "extras"
)
async def extras_callback(
    callback: CallbackQuery,
) -> None:
    await safe_edit(
        callback,
        "➕ *Добавки*\n\n"
        "Что хотите добавить?",
        await extras_keyboard(),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data == "extras:addons"
)
async def extras_addons_callback(
    callback: CallbackQuery,
) -> None:
    await safe_edit(
        callback,
        "➕ *Добавки*\n\n"
        "Все добавки — по *60 ₽*.",
        await standalone_addons_keyboard(),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data == "extras:sauces"
)
async def extras_sauces_callback(
    callback: CallbackQuery,
) -> None:
    await safe_edit(
        callback,
        "🥫 *Соусы*\n\n"
        "Все дополнительные соусы — по *60 ₽*.",
        await standalone_sauces_keyboard(),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data.startswith("extra:addon:")
)
async def standalone_addon_callback(
    callback: CallbackQuery,
) -> None:
    addon_id = callback.data.split(
        ":",
        2,
    )[2]

    addon = await find_addon(
        addon_id
    )

    if not addon:
        await safe_answer_callback(
            callback,
            "Добавка не найдена",
            True,
        )
        return

    add_to_cart(
        callback.from_user.id,
        {
            "product_id": f"addon_{addon_id}",
            "name": f"Добавка: {addon['name']}",
            "base_price": addon["price"],
            "total_price": addon["price"],
            "details": [],
        },
    )

    await safe_answer_callback(
        callback,
        f"{addon['name']} добавлено ✅",
    )


@router.callback_query(
    F.data.startswith("extra:sauce:")
)
async def standalone_sauce_callback(
    callback: CallbackQuery,
) -> None:
    sauce_id = callback.data.split(
        ":",
        2,
    )[2]

    sauce = await find_sauce(
        sauce_id
    )

    if not sauce:
        await safe_answer_callback(
            callback,
            "Соус не найден",
            True,
        )
        return

    add_to_cart(
        callback.from_user.id,
        {
            "product_id": f"sauce_{sauce_id}",
            "name": f"Соус: {sauce['name']}",
            "base_price": sauce["price"],
            "total_price": sauce["price"],
            "details": [],
        },
    )

    await safe_answer_callback(
        callback,
        f"{sauce['name']} добавлен ✅",
    )
@router.callback_query(
    F.data == "cart"
)
async def cart_callback(
    callback: CallbackQuery,
) -> None:
    cart = get_cart(
        callback.from_user.id
    )

    await safe_edit(
        callback,
        format_cart(
            callback.from_user.id
        ),
        cart_keyboard(
            len(cart)
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data.startswith("cart:remove:")
)
async def cart_remove_callback(
    callback: CallbackQuery,
) -> None:
    try:
        index = int(
            callback.data.split(
                ":",
                2,
            )[2]
        )
    except ValueError:
        await safe_answer_callback(
            callback,
            "Не удалось определить позицию",
            True,
        )
        return

    cart = get_cart(
        callback.from_user.id
    )

    if (
        index < 0
        or index >= len(cart)
    ):
        await safe_answer_callback(
            callback,
            "Этой позиции уже нет",
            True,
        )
        return

    removed = cart.pop(index)

    await safe_edit(
        callback,
        format_cart(
            callback.from_user.id
        ),
        cart_keyboard(
            len(cart)
        ),
    )

    await safe_answer_callback(
        callback,
        f"Удалено: {removed['name']}",
    )


@router.callback_query(
    F.data == "cart:clear"
)
async def cart_clear_callback(
    callback: CallbackQuery,
) -> None:
    clear_cart(
        callback.from_user.id
    )

    await safe_edit(
        callback,
        "🛒 *Корзина очищена*",
        cart_keyboard(0),
    )

    await safe_answer_callback(
        callback,
        "Корзина очищена",
    )


@router.callback_query(
    F.data == "checkout"
)
async def checkout_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    cart = get_cart(
        callback.from_user.id
    )

    if not cart:
        await safe_answer_callback(
            callback,
            "Корзина пустая",
            True,
        )
        return

    await state.clear()

    await state.set_state(
        CheckoutState.waiting_name
    )

    await callback.message.answer(
        "👤 *Как вас зовут?*\n\n"
        "Напишите имя одним сообщением."
    )

    await safe_answer_callback(callback)


@router.message(
    CheckoutState.waiting_name
)
async def checkout_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    name = (
        message.text
        or ""
    ).strip()

    if len(name) < 2:
        await message.answer(
            "⚠️ Имя слишком короткое.\n\n"
            "Напишите имя ещё раз."
        )
        return

    if len(name) > 60:
        await message.answer(
            "⚠️ Имя слишком длинное.\n\n"
            "Введите более короткий вариант."
        )
        return

    await state.update_data(
        customer_name=name
    )

    await state.set_state(
        CheckoutState.waiting_phone
    )

    await message.answer(
        "☎️ *Введите номер телефона*\n\n"
        "Например: `+7 912 123-45-67`"
    )


@router.message(
    CheckoutState.waiting_phone
)
async def checkout_phone_handler(
    message: Message,
    state: FSMContext,
) -> None:
    phone = (
        message.text
        or ""
    ).strip()

    digits = "".join(
        character
        for character in phone
        if character.isdigit()
    )

    if len(digits) < 10:
        await message.answer(
            "⚠️ Номер телефона выглядит "
            "неполным.\n\n"
            "Введите его ещё раз."
        )
        return

    if len(digits) > 15:
        await message.answer(
            "⚠️ В номере слишком много цифр.\n\n"
            "Введите его ещё раз."
        )
        return

    await state.update_data(
        customer_phone=phone
    )

    await state.set_state(
        CheckoutState.waiting_pickup
    )

    await message.answer(
        "⏰ *Через сколько вы подойдёте?*\n\n"
        "Например:\n"
        "• `через 20 минут`\n"
        "• `через час`\n"
        "• `в 18:30`"
    )


@router.message(
    CheckoutState.waiting_pickup
)
async def checkout_pickup_handler(
    message: Message,
    state: FSMContext,
) -> None:
    pickup = (
        message.text
        or ""
    ).strip()

    if len(pickup) < 2:
        await message.answer(
            "⚠️ Укажите время самовывоза."
        )
        return

    if len(pickup) > 80:
        await message.answer(
            "⚠️ Напишите время короче.\n\n"
            "Например: `через 30 минут`."
        )
        return

    await state.update_data(
        pickup=pickup
    )

    await state.set_state(
        CheckoutState.waiting_confirmation
    )

    data = await state.get_data()

    text = (
        f"{format_cart(message.from_user.id)}\n\n"
        "──────────────\n"
        "📋 *Данные для заказа*\n\n"
        f"👤 Имя: *{data['customer_name']}*\n"
        f"☎️ Телефон: *{data['customer_phone']}*\n"
        f"⏰ Самовывоз: *{pickup}*\n\n"
        "Проверьте заказ и нажмите "
        "кнопку подтверждения."
    )

    await message.answer(
        text,
        reply_markup=(
            confirm_order_keyboard()
        ),
    )


@router.callback_query(
    F.data == "order:cancel"
)
async def order_cancel_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    cart = get_cart(
        callback.from_user.id
    )

    await safe_edit(
        callback,
        (
            "❌ *Оформление отменено*\n\n"
            "Товары не удалены и "
            "остались в корзине."
        ),
        cart_keyboard(
            len(cart)
        ),
    )

    await safe_answer_callback(
        callback,
        "Оформление отменено",
    )
    @router.callback_query(
    CheckoutState.waiting_confirmation,
    F.data == "order:confirm",
)
async def order_confirm_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    user_id = callback.from_user.id
    cart = get_cart(user_id)

    if not cart:
        await safe_answer_callback(
            callback,
            "Корзина пустая",
            True,
        )
        return

    data = await state.get_data()

    required_fields = {
        "customer_name",
        "customer_phone",
        "pickup",
    }

    if not required_fields.issubset(
        data.keys()
    ):
        await state.clear()

        await safe_answer_callback(
            callback,
            "Данные заказа устарели",
            True,
        )
        return

    total = cart_total(user_id)

    order_data = {
        "telegram_id": user_id,
        "username": (
            callback.from_user.username
            or ""
        ),
        "customer_name": (
            data["customer_name"]
        ),
        "phone": (
            data["customer_phone"]
        ),
        "pickup": (
            data["pickup"]
        ),
        "total": total,
        "items": cart.copy(),
    }

    try:
        saved_order = await storage.save_order(
            order_data
        )
    except Exception:
        logging.exception(
            "Ошибка сохранения заказа"
        )

        await safe_answer_callback(
            callback,
            "Не удалось сохранить заказ",
            True,
        )
        return

    order_id = saved_order[
        "order_id"
    ]

    notification = (
        f"🔥 *НОВЫЙ ЗАКАЗ №{order_id}*\n\n"
        f"{format_cart(user_id)}\n\n"
        "──────────────\n"
        f"👤 Имя: "
        f"*{saved_order['customer_name']}*\n"
        f"☎️ Телефон: "
        f"*{saved_order['phone']}*\n"
        f"⏰ Самовывоз: "
        f"*{saved_order['pickup']}*\n\n"
        f"🆔 Telegram ID: `{user_id}`"
    )

    recipients = set(
        ADMIN_IDS + KITCHEN_IDS
    )

    for recipient_id in recipients:
        try:
            await bot.send_message(
                recipient_id,
                notification,
                reply_markup=(
                    kitchen_order_keyboard(
                        order_id
                    )
                ),
            )
        except Exception:
            logging.exception(
                "Не удалось отправить заказ "
                "получателю %s",
                recipient_id,
            )

    clear_cart(user_id)
    await state.clear()

    await safe_edit(
        callback,
        (
            f"✅ *Заказ №{order_id} принят!*\n\n"
            f"💵 Сумма: *{total} ₽*\n"
            f"⏰ Самовывоз: "
            f"*{saved_order['pickup']}*\n\n"
            "Мы передали заказ на кухню.\n"
            "Оплата — при получении ❤️"
        ),
        main_menu_keyboard(
            is_admin(
                user_id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(
        callback,
        "Заказ оформлен ✅",
    )


@router.callback_query(
    F.data.startswith("kitchen:")
)
async def kitchen_status_callback(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    if not is_staff(
        callback.from_user.id,
        ADMIN_IDS,
        KITCHEN_IDS,
    ):
        await safe_answer_callback(
            callback,
            "Нет доступа",
            True,
        )
        return

    try:
        _, status, order_id_text = (
            callback.data.split(
                ":",
                2,
            )
        )

        order_id = int(
            order_id_text
        )
    except ValueError:
        await safe_answer_callback(
            callback,
            "Ошибка номера заказа",
            True,
        )
        return

    stats = await storage.get_stats()

    order = next(
        (
            item
            for item in stats.get(
                "orders",
                [],
            )
            if item.get(
                "order_id"
            ) == order_id
        ),
        None,
    )

    if not order:
        await safe_answer_callback(
            callback,
            "Заказ не найден",
            True,
        )
        return

    customer_id = order.get(
        "telegram_id"
    )

    if status == "accept":
        try:
            await bot.send_message(
                customer_id,
                (
                    f"👨‍🍳 *Заказ №{order_id} "
                    "принят в работу!*\n\n"
                    "Мы начали его готовить."
                ),
            )
        except Exception:
            logging.exception(
                "Не удалось уведомить клиента"
            )

        await safe_answer_callback(
            callback,
            "Заказ принят в работу",
        )
        return

    if status == "ready":
        try:
            await bot.send_message(
                customer_id,
                (
                    f"✅ *Заказ №{order_id} готов!*\n\n"
                    "Можно забирать ❤️"
                ),
            )
        except Exception:
            logging.exception(
                "Не удалось уведомить клиента"
            )

        await safe_answer_callback(
            callback,
            "Клиент уведомлён ✅",
        )
        @router.callback_query(
    F.data == "address"
)
async def address_callback(
    callback: CallbackQuery,
) -> None:
    await safe_edit(
        callback,
        (
            "📍 *Наш адрес*\n\n"
            f"{ADDRESS}"
        ),
        main_menu_keyboard(
            is_admin(
                callback.from_user.id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data == "contact"
)
async def contact_callback(
    callback: CallbackQuery,
) -> None:
    await safe_edit(
        callback,
        (
            "☎️ *Связаться с нами*\n\n"
            f"{CONTACT}"
        ),
        main_menu_keyboard(
            is_admin(
                callback.from_user.id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data == "privacy"
)
async def privacy_callback(
    callback: CallbackQuery,
) -> None:
    text = (
        "🔒 *Политика конфиденциальности*\n\n"
        "Для оформления заказа бот "
        "может получать следующие данные:\n\n"
        "• имя\n"
        "• номер телефона\n"
        "• Telegram ID\n"
        "• состав заказа\n"
        "• время самовывоза\n\n"
        "Эти данные используются "
        "только для приёма и выполнения заказа.\n\n"
        "Информация не используется "
        "для рекламных рассылок "
        "и не передаётся посторонним лицам."
    )

    await safe_edit(
        callback,
        text,
        main_menu_keyboard(
            is_admin(
                callback.from_user.id,
                ADMIN_IDS,
            )
        ),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data == "admin"
)
async def admin_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(
        callback.from_user.id,
        ADMIN_IDS,
    ):
        await safe_answer_callback(
            callback,
            "Нет доступа",
            True,
        )
        return

    await safe_edit(
        callback,
        "⚙️ *Админ-панель*\n\n"
        "Выберите раздел:",
        admin_keyboard(),
    )

    await safe_answer_callback(callback)


@router.callback_query(
    F.data == "admin:stats"
)
async def admin_stats_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(
        callback.from_user.id,
        ADMIN_IDS,
    ):
        await safe_answer_callback(
            callback,
            "Нет доступа",
            True,
        )
        return

    try:
        stats = await storage.get_stats()
    except Exception:
        logging.exception(
            "Ошибка получения статистики"
        )

        await safe_answer_callback(
            callback,
            "Не удалось загрузить статистику",
            True,
        )
        return

    orders = stats.get(
        "orders",
        [],
    )

    total_orders = int(
        stats.get(
            "total_orders",
            0,
        )
    )

    total_revenue = int(
        stats.get(
            "total_revenue",
            0,
        )
    )

    if total_orders:
        average_check = round(
            total_revenue
            / total_orders
        )
    else:
        average_check = 0

    today = datetime.now().date()

    today_orders = 0
    today_revenue = 0

    for order in orders:
        created_at = order.get(
            "created_at"
        )

        if not created_at:
            continue

        try:
            order_date = (
                datetime.fromisoformat(
                    created_at
                ).date()
            )
        except ValueError:
            continue

        if order_date == today:
            today_orders += 1

            today_revenue += int(
                order.get(
                    "total",
                    0,
                )
            )

    text = (
        "📊 *Статистика Кайф Шаурма*\n\n"
        "📅 *Сегодня*\n"
        f"🧾 Заказов: *{today_orders}*\n"
        f"💰 Выручка: *{today_revenue} ₽*\n\n"
        "📈 *За всё время*\n"
        f"🧾 Заказов: *{total_orders}*\n"
        f"💰 Выручка: *{total_revenue} ₽*\n"
        f"🧮 Средний чек: *{average_check} ₽*"
    )

    if orders:
        last_order = orders[-1]

        text += (
            "\n\n"
            "🕒 *Последний заказ*\n"
            f"№{last_order.get('order_id', '—')}\n"
            f"👤 "
            f"{last_order.get('customer_name', '—')}\n"
            f"💵 "
            f"{last_order.get('total', 0)} ₽\n"
            f"⏰ "
            f"{last_order.get('pickup', '—')}"
        )

    await safe_edit(
        callback,
        text,
        admin_keyboard(),
    )

    await safe_answer_callback(callback)


@router.errors()
async def error_handler(
    event: ErrorEvent,
) -> bool:
    logging.error(
        "Необработанная ошибка: %s",
        event.exception,
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        ),
    )

    try:
        if event.update.callback_query:
            await safe_answer_callback(
                event.update.callback_query,
                (
                    "Произошла ошибка. "
                    "Попробуйте ещё раз."
                ),
                True,
            )

        elif event.update.message:
            await event.update.message.answer(
                "⚠️ Произошла ошибка.\n\n"
                "Попробуйте ещё раз "
                "или отправьте /start."
            )

    except Exception:
        logging.exception(
            "Не удалось сообщить "
            "пользователю об ошибке"
        )

    return True
