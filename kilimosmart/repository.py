"""Local, offline-friendly persistence for farmer profiles and their
recommendation history.

Stands in for the SMS/USSD gateway's subscriber store — a JSON file keeps
the prototype dependency-free and runnable without a database.
"""

import json
from pathlib import Path

from kilimosmart.models import Farmer, RecommendationLog

DEFAULT_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "farmers.json"
MAX_HISTORY_PER_FARMER = 10


class FarmerRepository:
    def __init__(self, store_path: Path = DEFAULT_STORE_PATH):
        self._path = store_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"farmers": {}, "history": {}})

    def _read(self) -> dict:
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("farmers", {})
        data.setdefault("history", {})
        return data

    def _write(self, data: dict) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save(self, farmer: Farmer) -> None:
        data = self._read()
        data["farmers"][farmer.phone] = farmer.to_dict()
        self._write(data)

    def get(self, phone: str) -> Farmer | None:
        data = self._read()
        record = data["farmers"].get(phone)
        return Farmer.from_dict(record) if record else None

    def exists(self, phone: str) -> bool:
        return phone in self._read()["farmers"]

    def all(self) -> list[Farmer]:
        return [Farmer.from_dict(record) for record in self._read()["farmers"].values()]

    def add_history(self, phone: str, log: RecommendationLog) -> None:
        data = self._read()
        entries = data["history"].setdefault(phone, [])
        entries.append(log.to_dict())
        data["history"][phone] = entries[-MAX_HISTORY_PER_FARMER:]
        self._write(data)

    def get_history(self, phone: str) -> list[RecommendationLog]:
        data = self._read()
        return [RecommendationLog.from_dict(entry) for entry in data["history"].get(phone, [])]
