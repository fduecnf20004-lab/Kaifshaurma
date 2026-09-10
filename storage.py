import asyncio
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from config import MENU_FILE, STATS_FILE


DEFAULT_STATS = {
    "total_orders": 0,
    "total_revenue": 0,
    "orders": [],
}


class JsonStorage:
    def __init__(self) -> None:
        self.menu_path = Path(MENU_FILE)
        self.stats_path = Path(STATS_FILE)
        self.lock = asyncio.Lock()

    async def initialize(self) -> None:
        self.menu_path.parent.mkdir(parents=True, exist_ok=True)
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.stats_path.exists():
            await self._write_json(
                self.stats_path,
                deepcopy(DEFAULT_STATS),
            )

        if not self.menu_path.exists():
            await self._write_json(self.menu_path, {})

    async def get_menu(self) -> dict[str, Any]:
        data = await self._read_json(self.menu_path, {})
        if not isinstance(data, dict):
            return {}
        return data

    async def get_stats(self) -> dict[str, Any]:
        data = await self._read_json(
            self.stats_path,
            deepcopy(DEFAULT_STATS),
        )

        if not isinstance(data, dict):
            return deepcopy(DEFAULT_STATS)

        data.setdefault("total_orders", 0)
        data.setdefault("total_revenue", 0)
        data.setdefault("orders", [])

        return data

    async def save_order(
        self,
        order: dict[str, Any],
    ) -> dict[str, Any]:
        async with self.lock:
            stats = await self.get_stats()

            order_data = deepcopy(order)
            order_data["created_at"] = datetime.now().isoformat(
                timespec="seconds"
            )

            stats["total_orders"] += 1
            order_data["order_id"] = stats["total_orders"]

            total = int(order_data.get("total", 0))
            stats["total_revenue"] += total
            stats["orders"].append(order_data)

            await self._write_json(self.stats_path, stats)

            return order_data

    async def _read_json(
        self,
        path: Path,
        default: Any,
    ) -> Any:
        try:
            text = await asyncio.to_thread(
                path.read_text,
                encoding="utf-8",
            )

            if not text.strip():
                return deepcopy(default)

            return json.loads(text)
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            return deepcopy(default)

    async def _write_json(
        self,
        path: Path,
        data: Any,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        text = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

        await asyncio.to_thread(
            path.write_text,
            text,
            encoding="utf-8",
        )


storage = JsonStorage()
