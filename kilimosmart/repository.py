"""Persistence for farm profiles and their recommendation history.

Backed by MySQL (served locally via XAMPP) rather than a JSON file, so the
data survives independently of the CLI process and mirrors how the
SMS/USSD gateway's subscriber store would be persisted in production.

A phone number can own several farms (e.g. a farmer with plots in
different regions), so each farm is its own row identified by a surrogate
`id`; `phone` is a plain indexed column, not the primary key.
"""

import os

from kilimosmart.models import Farmer, RecommendationLog

import mysql.connector

MAX_HISTORY_PER_FARM = 10

DB_CONFIG = {
    "host": os.environ.get("KILIMOSMART_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("KILIMOSMART_DB_PORT", "3306")),
    "user": os.environ.get("KILIMOSMART_DB_USER", "root"),
    "password": os.environ.get("KILIMOSMART_DB_PASSWORD", ""),
}
DEFAULT_DB_NAME = os.environ.get("KILIMOSMART_DB_NAME", "kilimosmart")


class FarmerRepository:
    def __init__(self, db_name: str = DEFAULT_DB_NAME):
        self._db_name = db_name
        self._ensure_database()
        self._ensure_schema()

    def _connect(self, use_database: bool = True):
        config = dict(DB_CONFIG)
        if use_database:
            config["database"] = self._db_name
        return mysql.connector.connect(**config)

    def _ensure_database(self) -> None:
        conn = self._connect(use_database=False)
        try:
            cur = conn.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self._db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS farmers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    region VARCHAR(100) NOT NULL,
                    farm_size_acres DOUBLE NOT NULL,
                    sms_opt_in TINYINT(1) NOT NULL DEFAULT 0,
                    registered_on VARCHAR(10) NOT NULL,
                    INDEX idx_phone (phone)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    farm_id INT NOT NULL,
                    timestamp VARCHAR(32) NOT NULL,
                    region VARCHAR(100) NOT NULL,
                    farm_size_acres DOUBLE NOT NULL,
                    top_crop VARCHAR(100) NOT NULL,
                    score DOUBLE NOT NULL,
                    estimated_profit DOUBLE NOT NULL,
                    INDEX idx_farm_id (farm_id),
                    FOREIGN KEY (farm_id) REFERENCES farmers(id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save(self, farmer: Farmer) -> Farmer:
        """Insert a new farm (when `farmer.id` is None) or update an
        existing one in place. Returns the farmer with `id` populated.
        """
        conn = self._connect()
        try:
            cur = conn.cursor()
            if farmer.id is None:
                cur.execute(
                    """
                    INSERT INTO farmers (phone, name, region, farm_size_acres, sms_opt_in, registered_on)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        farmer.phone,
                        farmer.name,
                        farmer.region,
                        farmer.farm_size_acres,
                        int(farmer.sms_opt_in),
                        farmer.registered_on,
                    ),
                )
                farmer.id = cur.lastrowid
            else:
                cur.execute(
                    """
                    UPDATE farmers
                    SET phone = %s, name = %s, region = %s, farm_size_acres = %s,
                        sms_opt_in = %s, registered_on = %s
                    WHERE id = %s
                    """,
                    (
                        farmer.phone,
                        farmer.name,
                        farmer.region,
                        farmer.farm_size_acres,
                        int(farmer.sms_opt_in),
                        farmer.registered_on,
                        farmer.id,
                    ),
                )
            conn.commit()
            return farmer
        finally:
            conn.close()

    def get(self, farm_id: int) -> Farmer | None:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, phone, name, region, farm_size_acres, sms_opt_in, registered_on "
                "FROM farmers WHERE id = %s",
                (farm_id,),
            )
            row = cur.fetchone()
            return self._farmer_from_row(row) if row else None
        finally:
            conn.close()

    def get_by_phone(self, phone: str) -> list[Farmer]:
        """All farms registered under a phone number, oldest first."""
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, phone, name, region, farm_size_acres, sms_opt_in, registered_on "
                "FROM farmers WHERE phone = %s ORDER BY id ASC",
                (phone,),
            )
            return [self._farmer_from_row(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def exists_for_phone(self, phone: str) -> bool:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM farmers WHERE phone = %s LIMIT 1", (phone,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def all(self) -> list[Farmer]:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, phone, name, region, farm_size_acres, sms_opt_in, registered_on FROM farmers"
            )
            return [self._farmer_from_row(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def delete(self, farm_id: int) -> None:
        """Remove a farm and its recommendation history (via ON DELETE CASCADE)."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM farmers WHERE id = %s", (farm_id,))
            conn.commit()
        finally:
            conn.close()

    def add_history(self, farm_id: int, log: RecommendationLog) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO recommendation_history
                    (farm_id, timestamp, region, farm_size_acres, top_crop, score, estimated_profit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    farm_id,
                    log.timestamp,
                    log.region,
                    log.farm_size_acres,
                    log.top_crop,
                    log.score,
                    log.estimated_profit,
                ),
            )
            cur.execute(
                """
                DELETE FROM recommendation_history
                WHERE farm_id = %s AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM recommendation_history
                        WHERE farm_id = %s
                        ORDER BY id DESC
                        LIMIT %s
                    ) AS keep_ids
                )
                """,
                (farm_id, farm_id, MAX_HISTORY_PER_FARM),
            )
            conn.commit()
        finally:
            conn.close()

    def get_history(self, farm_id: int) -> list[RecommendationLog]:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT timestamp, region, farm_size_acres, top_crop, score, estimated_profit
                FROM recommendation_history
                WHERE farm_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (farm_id, MAX_HISTORY_PER_FARM),
            )
            rows = cur.fetchall()
            rows.reverse()
            return [RecommendationLog(**row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _farmer_from_row(row: dict) -> Farmer:
        return Farmer(
            id=row["id"],
            phone=row["phone"],
            name=row["name"],
            region=row["region"],
            farm_size_acres=row["farm_size_acres"],
            sms_opt_in=bool(row["sms_opt_in"]),
            registered_on=row["registered_on"],
        )
