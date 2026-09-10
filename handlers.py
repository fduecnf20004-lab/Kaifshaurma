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
