import logging
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
