from typing import Any

from storage import storage


carts: dict[int, list[dict[str, Any]]] = {}


def is_admin(
    user_id: int,
    admin_ids: list[int],
) -> bool:
    return user_id in admin_ids


def is_staff(
    user_id: int,
    admin_ids: list[int],
    kitchen_ids: list[int],
) -> bool:
    return user_id in set(
        admin_ids + kitchen_ids
    )


def get_cart(
    user_id: int,
) -> list[dict[str, Any]]:
    return carts.setdefault(
        user_id,
        [],
    )


def clear_cart(
    user_id: int,
) -> None:
    carts[user_id] = []


def add_to_cart(
    user_id: int,
    item: dict[str, Any],
) -> None:
    get_cart(user_id).append(item)


def cart_total(
    user_id: int,
) -> int:
    return sum(
        int(
            item.get(
                "total_price",
                0,
            )
        )
        for item in get_cart(user_id)
    )


def format_product_name(
    product: dict[str, Any],
) -> str:
    name = product["name"]

    weight = product.get("weight")

    if weight and weight not in name:
        name += f", {weight}"

    volume = product.get("volume")

    if volume and volume not in name:
        name += f", {volume}"

    return name


def format_product_card(
    product: dict[str, Any],
) -> str:
    lines = [
        f"🌯 *{product['name']}*",
    ]

    if product.get("weight"):
        lines.append(
            f"⚖️ Вес: {product['weight']}"
        )

    if product.get("volume"):
        lines.append(
            f"🥤 Объём: {product['volume']}"
        )

    if product.get("description"):
        lines.append("")
        lines.append(
            product["description"]
        )

    if product.get("price") is not None:
        lines.append("")
        lines.append(
            f"💰 *{product['price']} ₽*"
        )

    return "\n".join(lines)


def format_cart(
    user_id: int,
) -> str:
    cart = get_cart(user_id)

    if not cart:
        return "🛒 *Корзина пока пустая*"

    lines = [
        "🛒 *Ваш заказ*",
        "",
    ]

    for index, item in enumerate(
        cart,
        1,
    ):
        lines.append(
            f"*{index}. {item['name']}*"
        )

        for detail in item.get(
            "details",
            [],
        ):
            if detail:
                lines.append(
                    f"• {detail}"
                )

        lines.append(
            f"💰 {item['total_price']} ₽"
        )
        lines.append("")

    lines.append(
        f"💵 *Итого: "
        f"{cart_total(user_id)} ₽*"
    )

    return "\n".join(lines)


async def get_menu() -> dict[str, Any]:
    return await storage.get_menu()


async def find_category(
    category_id: str,
) -> dict[str, Any] | None:
    menu = await get_menu()

    return next(
        (
            category
            for category in menu.get(
                "categories",
                [],
            )
            if category["id"]
            == category_id
        ),
        None,
    )


async def find_subcategory(
    category_id: str,
    subcategory_id: str,
) -> dict[str, Any] | None:
    category = await find_category(
        category_id
    )

    if not category:
        return None

    return next(
        (
            subcategory
            for subcategory
            in category.get(
                "subcategories",
                [],
            )
            if subcategory["id"]
            == subcategory_id
        ),
        None,
    )


async def find_product(
    product_id: str,
) -> dict[str, Any] | None:
    menu = await get_menu()

    for category in menu.get(
        "categories",
        [],
    ):
        for product in category.get(
            "items",
            [],
        ):
            if product["id"] == product_id:
                return product

        for subcategory in category.get(
            "subcategories",
            [],
        ):
            for product in subcategory.get(
                "items",
                [],
            ):
                if (
                    product["id"]
                    == product_id
                ):
                    return product

    return None


async def find_addon(
    addon_id: str,
) -> dict[str, Any] | None:
    menu = await get_menu()

    return next(
        (
            addon
            for addon in menu.get(
                "addons",
                [],
            )
            if addon["id"] == addon_id
        ),
        None,
    )


async def find_sauce(
    sauce_id: str,
) -> dict[str, Any] | None:
    menu = await get_menu()

    return next(
        (
            sauce
            for sauce in menu.get(
                "sauces",
                [],
            )
            if sauce["id"] == sauce_id
        ),
        None,
    )


async def find_coffee(
    coffee_id: str,
) -> dict[str, Any] | None:
    menu = await get_menu()

    return next(
        (
            coffee
            for coffee in menu.get(
                "coffee",
                [],
            )
            if coffee["id"] == coffee_id
        ),
        None,
    )
