import os


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

ADMIN_IDS = [
    6453170852,
]

KITCHEN_IDS = [
    6453170852,
]

NOTIFICATION_IDS = list(set(ADMIN_IDS + KITCHEN_IDS))

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "10000"))

MENU_FILE = "data/menu.json"
STATS_FILE = "data/stats.json"

BUSINESS_NAME = "Кайф Шаурма"

ADDRESS = "г.Ижевск, ул.Некрасова д.35 к.1"
CONTACT = "+7 992 223 77 68"
