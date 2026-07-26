"""Persistence for farmer profiles and their recommendation history.

Backed by MySQL (served locally via XAMPP) rather than a JSON file, so the
data survives independently of the CLI process and mirrors how the
SMS/USSD gateway's subscriber store would be persisted in production.
"""

import os

from kilimosmart.models import Farmer, RecommendationLog

import mysql.connector

MAX_HISTORY_PER_FARMER = 10

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
                    phone VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    region VARCHAR(100) NOT NULL,
                    farm_size_acres DOUBLE NOT NULL,
                    sms_opt_in TINYINT(1) NOT NULL DEFAULT 0,
                    registered_on VARCHAR(10) NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    timestamp VARCHAR(32) NOT NULL,
                    region VARCHAR(100) NOT NULL,
                    farm_size_acres DOUBLE NOT NULL,
                    top_crop VARCHAR(100) NOT NULL,
                    score DOUBLE NOT NULL,
                    estimated_profit DOUBLE NOT NULL,
                    INDEX idx_phone (phone)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save(self, farmer: Farmer) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO farmers (phone, name, region, farm_size_acres, sms_opt_in, registered_on)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    region = VALUES(region),
                    farm_size_acres = VALUES(farm_size_acres),
                    sms_opt_in = VALUES(sms_opt_in),
                    registered_on = VALUES(registered_on)
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
            conn.commit()
        finally:
            conn.close()

    def get(self, phone: str) -> Farmer | None:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT phone, name, region, farm_size_acres, sms_opt_in, registered_on "
                "FROM farmers WHERE phone = %s",
                (phone,),
            )
            row = cur.fetchone()
            return self._farmer_from_row(row) if row else None
        finally:
            conn.close()

    def exists(self, phone: str) -> bool:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM farmers WHERE phone = %s", (phone,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def all(self) -> list[Farmer]:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT phone, name, region, farm_size_acres, sms_opt_in, registered_on FROM farmers"
            )
            return [self._farmer_from_row(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def add_history(self, phone: str, log: RecommendationLog) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO recommendation_history
                    (phone, timestamp, region, farm_size_acres, top_crop, score, estimated_profit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    phone,
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
                WHERE phone = %s AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM recommendation_history
                        WHERE phone = %s
                        ORDER BY id DESC
                        LIMIT %s
                    ) AS keep_ids
                )
                """,
                (phone, phone, MAX_HISTORY_PER_FARMER),
            )
            conn.commit()
        finally:
            conn.close()

    def get_history(self, phone: str) -> list[RecommendationLog]:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT timestamp, region, farm_size_acres, top_crop, score, estimated_profit
                FROM recommendation_history
                WHERE phone = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (phone, MAX_HISTORY_PER_FARMER),
            )
            rows = cur.fetchall()
            rows.reverse()
            return [RecommendationLog(**row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _farmer_from_row(row: dict) -> Farmer:
        return Farmer(
            phone=row["phone"],
            name=row["name"],
            region=row["region"],
            farm_size_acres=row["farm_size_acres"],
            sms_opt_in=bool(row["sms_opt_in"]),
            registered_on=row["registered_on"],
        )
