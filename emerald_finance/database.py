from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "emerald_finance.db"


@dataclass(frozen=True)
class Summary:
    balance: float
    month_income: float
    month_expense: float
    open_debt: float
    monthly_interest: float
    overdue_debts: int
    unclassified: int


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    seed(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL,
            group_name TEXT NOT NULL,
            category TEXT NOT NULL,
            result_center TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Entrada','Saida','Transferencia')),
            essential INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            account_id INTEGER,
            source TEXT NOT NULL DEFAULT 'Manual',
            external_id TEXT UNIQUE,
            counterparty TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creditor TEXT NOT NULL,
            debt_type TEXT NOT NULL,
            opened_at TEXT,
            initial_balance REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            monthly_interest_rate REAL NOT NULL DEFAULT 0,
            minimum_payment REAL NOT NULL DEFAULT 0,
            due_date TEXT,
            strategy TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE,
            monthly_limit REAL NOT NULL DEFAULT 0,
            action_hint TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS import_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority INTEGER NOT NULL DEFAULT 100,
            contains_text TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        );
        """
    )
    conn.commit()


def seed(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] > 0:
        return

    accounts = [
        ("REC001", "Salario", "Receitas", "Renda fixa", "Resultado Operacional", "Entrada", 1),
        ("REC002", "Freelance", "Receitas", "Renda variavel", "Resultado Operacional", "Entrada", 0),
        ("MOR001", "Aluguel", "Moradia", "Moradia fixa", "Resultado Operacional", "Saida", 1),
        ("MOR002", "Condominio", "Moradia", "Moradia fixa", "Resultado Operacional", "Saida", 1),
        ("MOR003", "Energia e agua", "Moradia", "Servicos essenciais", "Resultado Operacional", "Saida", 1),
        ("MER001", "Supermercado", "Alimentacao", "Mercado", "Resultado Operacional", "Saida", 1),
        ("ALI001", "Restaurantes", "Alimentacao", "Lazer alimentar", "Resultado Variavel", "Saida", 0),
        ("TRA001", "Transporte app", "Transporte", "Mobilidade", "Resultado Operacional", "Saida", 0),
        ("SAU001", "Farmacia", "Saude", "Saude", "Resultado Operacional", "Saida", 1),
        ("LAZ001", "Streaming", "Lazer", "Assinaturas", "Resultado Variavel", "Saida", 0),
        ("DIV001", "Pagamento cartao", "Dividas", "Cartao de credito", "Resultado Financeiro", "Saida", 1),
        ("DIV002", "Pagamento emprestimo", "Dividas", "Emprestimos", "Resultado Financeiro", "Saida", 1),
        ("INV001", "Investimentos", "Investimentos", "Aportes", "Alocacao Patrimonial", "Saida", 0),
        ("OUT001", "Outros", "Outros", "Nao classificado", "Resultado Variavel", "Saida", 0),
    ]
    conn.executemany(
        """
        INSERT INTO accounts
        (code, name, group_name, category, result_center, type, essential)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        accounts,
    )

    account_ids = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM accounts")}
    today = date.today()
    month_start = today.replace(day=1)
    demo_transactions = [
        (month_start.replace(day=5).isoformat(), "Salario mensal", 7200, "Salario", "Manual", None, None, ""),
        (month_start.replace(day=6).isoformat(), "Aluguel", -1850, "Aluguel", "Manual", None, None, ""),
        (month_start.replace(day=8).isoformat(), "Supermercado", -742.56, "Supermercado", "Manual", None, None, ""),
        (month_start.replace(day=10).isoformat(), "Restaurante", -118.4, "Restaurantes", "Manual", None, None, ""),
        (month_start.replace(day=11).isoformat(), "Uber", -86.2, "Transporte app", "Manual", None, None, ""),
        (month_start.replace(day=12).isoformat(), "Pagamento fatura cartao", -800, "Pagamento cartao", "Manual", None, "Cartao principal", ""),
        (month_start.replace(day=15).isoformat(), "Freelance", 950, "Freelance", "Manual", None, None, ""),
        (month_start.replace(day=16).isoformat(), "Aporte investimento", -900, "Investimentos", "Manual", None, None, ""),
    ]
    conn.executemany(
        """
        INSERT INTO transactions
        (tx_date, description, amount, account_id, source, external_id, counterparty, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(d, desc, amount, account_ids[acc], src, ext, cp, note) for d, desc, amount, acc, src, ext, cp, note in demo_transactions],
    )

    debts = [
        ("Cartao principal", "Cartao", (today - timedelta(days=50)).isoformat(), 4200, 1300, 12.9, 800, (today + timedelta(days=6)).isoformat(), "Priorizar se juros rotativo"),
        ("Emprestimo pessoal", "Emprestimo", (today - timedelta(days=120)).isoformat(), 9800, 2600, 3.2, 620, (today + timedelta(days=13)).isoformat(), "Avaliar amortizacao extra"),
        ("Parcelamento compra", "Parcelamento", (today - timedelta(days=70)).isoformat(), 2100, 700, 1.8, 350, (today + timedelta(days=21)).isoformat(), "Manter em dia"),
    ]
    conn.executemany(
        """
        INSERT INTO debts
        (creditor, debt_type, opened_at, initial_balance, paid_amount, monthly_interest_rate, minimum_payment, due_date, strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        debts,
    )

    budgets = [
        ("Moradia fixa", 2300, "Revisar aluguel, condominio e contratos"),
        ("Mercado", 1300, "Separar compras essenciais de conveniencia"),
        ("Lazer alimentar", 650, "Controlar delivery e restaurantes"),
        ("Mobilidade", 420, "Monitorar apps e combustivel"),
        ("Saude", 350, "Manter reserva para farmacia/consultas"),
        ("Assinaturas", 180, "Cancelar o que nao usa"),
        ("Cartao de credito", 900, "Priorizar maior taxa"),
        ("Aportes", 900, "Automatizar aporte"),
    ]
    conn.executemany("INSERT INTO budgets (category, monthly_limit, action_hint) VALUES (?, ?, ?)", budgets)

    rules = [
        (1, "SALARIO", "Salario"),
        (2, "FREELANCE", "Freelance"),
        (3, "ALUGUEL", "Aluguel"),
        (4, "CONDOMINIO", "Condominio"),
        (5, "MERCADO", "Supermercado"),
        (6, "CARREFOUR", "Supermercado"),
        (7, "IFOOD", "Restaurantes"),
        (8, "UBER", "Transporte app"),
        (9, "FARMACIA", "Farmacia"),
        (10, "NETFLIX", "Streaming"),
        (11, "CARTAO", "Pagamento cartao"),
        (12, "EMPRESTIMO", "Pagamento emprestimo"),
    ]
    conn.executemany(
        "INSERT INTO import_rules (priority, contains_text, account_id) VALUES (?, ?, ?)",
        [(p, text, account_ids[acc]) for p, text, acc in rules],
    )
    conn.commit()


def rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return list(conn.execute(sql, params))


def current_month_bounds() -> tuple[str, str]:
    start = date.today().replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat()


def get_summary(conn: sqlite3.Connection) -> Summary:
    start, end = current_month_bounds()
    balance = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions").fetchone()[0]
    month_income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE amount > 0 AND tx_date >= ? AND tx_date < ?",
        (start, end),
    ).fetchone()[0]
    month_expense = abs(
        conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE amount < 0 AND tx_date >= ? AND tx_date < ?",
            (start, end),
        ).fetchone()[0]
    )
    open_debt = conn.execute("SELECT COALESCE(SUM(MAX(initial_balance - paid_amount, 0)), 0) FROM debts WHERE active = 1").fetchone()[0]
    monthly_interest = conn.execute(
        "SELECT COALESCE(SUM(MAX(initial_balance - paid_amount, 0) * monthly_interest_rate / 100.0), 0) FROM debts WHERE active = 1"
    ).fetchone()[0]
    overdue_debts = conn.execute(
        "SELECT COUNT(*) FROM debts WHERE active = 1 AND due_date < ? AND initial_balance > paid_amount",
        (date.today().isoformat(),),
    ).fetchone()[0]
    unclassified = conn.execute("SELECT COUNT(*) FROM transactions WHERE account_id IS NULL").fetchone()[0]
    return Summary(balance, month_income, month_expense, open_debt, monthly_interest, overdue_debts, unclassified)


def find_account_for_description(conn: sqlite3.Connection, description: str) -> int | None:
    normalized = description.upper()
    for rule in conn.execute(
        """
        SELECT r.contains_text, r.account_id
        FROM import_rules r
        WHERE r.active = 1
        ORDER BY r.priority ASC
        """
    ):
        if rule["contains_text"].upper() in normalized:
            return int(rule["account_id"])
    account = conn.execute("SELECT id FROM accounts WHERE name = 'Outros'").fetchone()
    return int(account["id"]) if account else None


def add_transaction(
    conn: sqlite3.Connection,
    tx_date: str,
    description: str,
    amount: float,
    account_id: int | None,
    source: str = "Manual",
    external_id: str | None = None,
    counterparty: str | None = None,
    notes: str | None = None,
) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO transactions
            (tx_date, description, amount, account_id, source, external_id, counterparty, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tx_date, description, amount, account_id, source, external_id, counterparty, notes),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def export_backup(conn: sqlite3.Connection, output_path: Path) -> None:
    payload: dict[str, list[dict[str, Any]]] = {}
    for table in ["accounts", "transactions", "debts", "budgets", "import_rules"]:
        payload[table] = [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_transactions_csv(conn: sqlite3.Connection, output_path: Path) -> None:
    query = """
        SELECT t.tx_date, t.description, t.amount, a.name AS account, a.group_name,
               a.category, a.result_center, a.type, t.source, t.external_id, t.counterparty, t.notes
        FROM transactions t
        LEFT JOIN accounts a ON a.id = t.account_id
        ORDER BY t.tx_date DESC, t.id DESC
    """
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["data", "descricao", "valor", "conta", "grupo", "categoria", "resultado", "tipo", "origem", "id_externo", "credor_projeto", "observacao"])
        for row in conn.execute(query):
            writer.writerow(list(row))


def add_debt_payment(conn: sqlite3.Connection, debt_id: int, amount: float) -> None:
    debt = conn.execute("SELECT * FROM debts WHERE id = ?", (debt_id,)).fetchone()
    if not debt:
        return
    conn.execute("UPDATE debts SET paid_amount = MIN(initial_balance, paid_amount + ?) WHERE id = ?", (amount, debt_id))
    account_id = conn.execute("SELECT id FROM accounts WHERE name = 'Pagamento emprestimo'").fetchone()
    account = int(account_id["id"]) if account_id else None
    add_transaction(
        conn,
        date.today().isoformat(),
        f"Pagamento - {debt['creditor']}",
        -abs(amount),
        account,
        "Manual",
        None,
        debt["creditor"],
        "Pagamento registrado pela tela de dividas",
    )
