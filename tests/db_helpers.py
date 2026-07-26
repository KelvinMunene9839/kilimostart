"""Shared MySQL test-database helpers.

Tests share the single XAMPP MySQL instance, running against a dedicated
`kilimosmart_test` database that gets wiped between tests so cases stay
isolated from each other and from the real `kilimosmart` data.
"""

import mysql.connector

from kilimosmart.repository import DB_CONFIG, FarmerRepository

TEST_DB_NAME = "kilimosmart_test"


def new_test_repository() -> FarmerRepository:
    repo = FarmerRepository(db_name=TEST_DB_NAME)
    clear_test_db()
    return repo


def clear_test_db() -> None:
    conn = mysql.connector.connect(database=TEST_DB_NAME, **DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM recommendation_history")
        cur.execute("DELETE FROM farmers")
        conn.commit()
    finally:
        conn.close()
