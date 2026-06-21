from __future__ import annotations

import sqlite3
from datetime import date


def money(value: float | int | None) -> str:
    number = float(value or 0)
    text = f"R$ {number:,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value: float | int | None) -> str:
    return f"{float(value or 0):.2f}%".replace(".", ",")


def debt_status(row: sqlite3.Row) -> str:
    remaining = max(float(row["initial_balance"]) - float(row["paid_amount"]), 0)
    if remaining <= 0:
        return "Quitada"
    due_date = row["due_date"]
    if not due_date:
        return "Sem vencimento"
    days = (date.fromisoformat(due_date) - date.today()).days
    if days < 0:
        return "Vencida"
    if days <= 7:
        return "Vence em 7 dias"
    return "Em aberto"


def month_label(iso_date: str) -> str:
    year, month, *_ = iso_date.split("-")
    return f"{month}/{year}"
