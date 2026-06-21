from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    group_name TEXT NOT NULL,
    category TEXT NOT NULL,
    result_center TEXT NOT NULL,
    type TEXT NOT NULL,
    essential BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT PRIMARY KEY,
    tx_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    account_id BIGINT REFERENCES accounts(id),
    source TEXT NOT NULL DEFAULT 'Manual',
    external_id TEXT UNIQUE,
    counterparty TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS debts (
    id BIGINT PRIMARY KEY,
    creditor TEXT NOT NULL,
    debt_type TEXT NOT NULL,
    opened_at DATE,
    initial_balance NUMERIC(14, 2) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    monthly_interest_rate NUMERIC(8, 4) NOT NULL DEFAULT 0,
    minimum_payment NUMERIC(14, 2) NOT NULL DEFAULT 0,
    due_date DATE,
    strategy TEXT,
    source TEXT NOT NULL DEFAULT 'Manual',
    external_id TEXT UNIQUE,
    notes TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS budgets (
    id BIGINT PRIMARY KEY,
    category TEXT UNIQUE NOT NULL,
    monthly_limit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    action_hint TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS import_rules (
    id BIGINT PRIMARY KEY,
    priority INTEGER NOT NULL DEFAULT 100,
    contains_text TEXT NOT NULL,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    active BOOLEAN NOT NULL DEFAULT TRUE
);
"""


TABLES = {
    "accounts": ["id", "code", "name", "group_name", "category", "result_center", "type", "essential", "active"],
    "transactions": ["id", "tx_date", "description", "amount", "account_id", "source", "external_id", "counterparty", "notes", "created_at"],
    "debts": [
        "id",
        "creditor",
        "debt_type",
        "opened_at",
        "initial_balance",
        "paid_amount",
        "monthly_interest_rate",
        "minimum_payment",
        "due_date",
        "strategy",
        "source",
        "external_id",
        "notes",
        "active",
    ],
    "budgets": ["id", "category", "monthly_limit", "action_hint", "active"],
    "import_rules": ["id", "priority", "contains_text", "account_id", "active"],
}

BOOLEAN_COLUMNS = {
    ("accounts", "essential"),
    ("accounts", "active"),
    ("debts", "active"),
    ("budgets", "active"),
    ("import_rules", "active"),
}


def load_database_url() -> str:
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def sync_sqlite_to_postgres(sqlite_conn: sqlite3.Connection, database_url: str | None = None) -> dict[str, int]:
    url = database_url or load_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL nao configurada. Crie um arquivo .env ou defina a variavel de ambiente.")

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Instale as dependencias opcionais: pip install -r requirements.txt") from exc

    sqlite_conn.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    with psycopg.connect(url) as pg_conn:
        with pg_conn.cursor() as cursor:
            cursor.execute(POSTGRES_SCHEMA)
            for table, columns in TABLES.items():
                source_rows = [dict(row) for row in sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table}")]
                counts[table] = len(source_rows)
                if not source_rows:
                    continue
                placeholders = ", ".join(["%s"] * len(columns))
                column_list = ", ".join(columns)
                update_list = ", ".join(f"{column}=EXCLUDED.{column}" for column in columns if column != "id")
                sql = f"""
                    INSERT INTO {table} ({column_list})
                    VALUES ({placeholders})
                    ON CONFLICT (id) DO UPDATE SET {update_list}
                """
                for row in source_rows:
                    values = [normalize_value(row[column], table, column) for column in columns]
                    cursor.execute(sql, values)
        pg_conn.commit()
    return counts


def normalize_value(value: Any, table: str, column: str) -> Any:
    if (table, column) in BOOLEAN_COLUMNS:
        return bool(value)
    return value
