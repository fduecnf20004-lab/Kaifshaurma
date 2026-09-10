from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from storage import storage


def build_keyboard(
    buttons: list[InlineKeyboardButton],
    row_size: int = 2,
    footer: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for button in buttons:
        row.append(button)

        if len(row) == row_size:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    if footer:
        rows.extend(footer)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard(
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="🌯 Меню",
                callback_data="menu",
            ),
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="cart",
            ),
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавки",
                callback_data="extras",
            ),
            InlineKeyboardButton(
                text="📍 Адрес",
                callback_data="address",
            ),
        ],
        [
            InlineKeyboardButton(
                text="☎️ Связаться",
                callback_data="contact",
            ),
            InlineKeyboardButton(
                text="🔒 Политика",
                callback_data="privacy",
            ),
        ],
    ]

    if is_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⚙️ Админ-панель",
                    callback_data="admin",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def categories_keyboard() -> InlineKeyboardMarkup:
    menu = await storage.get_menu()
    categories = menu.get("categories", [])

    buttons = []

    for category in categories:
        buttons.append(
            InlineKeyboardButton(
                text=category.get(
                    "short_name",
                    category["name"],
                ),
                callback_data=f"category:{category['id']}",
            )
        )

    footer = [
        [
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="cart",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="home",
            )
        ],
    ]

    return build_keyboard(
        buttons=buttons,
        row_size=2,
        footer=footer,
    )


async def subcategories_keyboard(
    category_id: str,
) -> InlineKeyboardMarkup:
    menu = await storage.get_menu()

    category = next(
        (
            item
            for item in menu.get("categories", [])
            if item["id"] == category_id
        ),
        None,
    )

    buttons = []

    if category:
        for subcategory in category.get(
            "subcategories",
            [],
        ):
            buttons.append(
                InlineKeyboardButton(
                    text=subcategory.get(
                        "short_name",
                        subcategory["name"],
                    ),
                    callback_data=(
                        f"subcategory:{category_id}:"
                        f"{subcategory['id']}"
                    ),
                )
            )

    footer = [
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="menu",
            ),
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="cart",
            ),
        ]
    ]

    return build_keyboard(
        buttons=buttons,
        row_size=2,
        footer=footer,
    )


def product_button_text(product: dict) -> str:
    text = product.get(
        "short_name",
        product["name"],
    )

    if product.get("weight"):
        if product["weight"] not in text:
            text += f" · {product['weight']}"

    if product.get("volume"):
        if product["volume"] not in text:
            text += f" · {product['volume']}"

    price = product.get("price")

    if price is not None:
        text += f" · {price} ₽"

    return text


def products_keyboard(
    products: list[dict],
    back_callback: str,
) -> InlineKeyboardMarkup:
    rows = []

    for product in products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=product_button_text(product),
                    callback_data=f"product:{product['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=back_callback,
            ),
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="cart",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def shawarma_options_keyboard(
    selected_addons: set[str],
    selected_sauce: str | None,
) -> InlineKeyboardMarkup:
    menu = await storage.get_menu()

    rows = []

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Добавки",
                callback_data="shawarma:addons",
            ),
            InlineKeyboardButton(
                text=(
                    "🥫 Соус ✅"
                    if selected_sauce
                    else "🥫 Соус"
                ),
                callback_data="shawarma:sauces",
            ),
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text=(
                    f"✅ Добавки: {len(selected_addons)}"
                    if selected_addons
                    else "Добавки не выбраны"
                ),
                callback_data="shawarma:addons",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="✅ В корзину",
                callback_data="shawarma:done",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def shawarma_addons_keyboard(
    selected_addons: set[str],
) -> InlineKeyboardMarkup:
    menu = await storage.get_menu()
    addons = menu.get("addons", [])

    rows = []

    for addon in addons:
        selected = addon["id"] in selected_addons

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{'✅' if selected else '➕'} "
                        f"{addon.get('short_name', addon['name'])} "
                        f"· {addon['price']} ₽"
                    ),
                    callback_data=f"shawarma:addon:{addon['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к шаурме",
                callback_data="shawarma:options",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def sauces_keyboard(
    target: str,
    selected_sauce: str | None = None,
) -> InlineKeyboardMarkup:
    menu = await storage.get_menu()
    sauces = menu.get("sauces", [])

    rows = []

    for sauce in sauces:
        selected = sauce["id"] == selected_sauce

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{'✅' if selected else '🥫'} "
                        f"{sauce.get('short_name', sauce['name'])}"
                    ),
                    callback_data=(
                        f"sauce:{target}:{sauce['id']}"
                    ),
                )
            ]
        )

    back_callback = (
        "shawarma:options"
        if target == "shawarma"
        else "menu"
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=back_callback,
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def coffee_keyboard(
    product_id: str,
) -> InlineKeyboardMarkup:
    menu = await storage.get_menu()
    coffee = menu.get("coffee", [])

    rows = []

    for item in coffee:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{item.get('short_name', item['name'])} "
                        f"· {item['volume']}"
                    ),
                    callback_data=(
                        f"coffee:{product_id}:{item['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="category:combos",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def extras_keyboard() -> InlineKeyboardMarkup:
    menu = await storage.get_menu()

    rows = [
        [
            InlineKeyboardButton(
                text="➕ Добавки",
                callback_data="extras:addons",
            ),
            InlineKeyboardButton(
                text="🥫 Соусы",
                callback_data="extras:sauces",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Главное меню",
                callback_data="home",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def standalone_addons_keyboard() -> InlineKeyboardMarkup:
    menu = await storage.get_menu()
    addons = menu.get("addons", [])

    rows = []

    for addon in addons:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{addon.get('short_name', addon['name'])} "
                        f"· {addon['price']} ₽"
                    ),
                    callback_data=f"extra:addon:{addon['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="extras",
            ),
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="cart",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def standalone_sauces_keyboard() -> InlineKeyboardMarkup:
    menu = await storage.get_menu()
    sauces = menu.get("sauces", [])

    rows = []

    for sauce in sauces:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{sauce.get('short_name', sauce['name'])} "
                        f"· {sauce['price']} ₽"
                    ),
                    callback_data=f"extra:sauce:{sauce['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="extras",
            ),
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="cart",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart_keyboard(
    cart_size: int,
) -> InlineKeyboardMarkup:
    rows = []

    for index in range(cart_size):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"❌ Удалить №{index + 1}",
                    callback_data=f"cart:remove:{index}",
                )
            ]
        )

    if cart_size:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Оформить заказ",
                    callback_data="checkout",
                )
            ]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 Очистить корзину",
                    callback_data="cart:clear",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🌯 Продолжить покупки",
                callback_data="menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить заказ",
                    callback_data="order:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить оформление",
                    callback_data="order:cancel",
                )
            ],
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin:stats",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="home",
                )
            ],
        ]
    )
