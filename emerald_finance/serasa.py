from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SerasaDebt:
    creditor: str
    debt_type: str
    initial_balance: float
    paid_amount: float
    monthly_interest_rate: float
    minimum_payment: float
    due_date: str | None
    status: str
    contract: str
    notes: str
    external_id: str


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def read_serasa_debts(path: Path) -> list[SerasaDebt]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="ignore")
    if "\ufffd" in text:
        text = raw.decode("latin-1", errors="ignore")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,") if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames:
        return []

    debts = []
    for row in reader:
        normalized = {normalize(key): (value or "").strip() for key, value in row.items() if key is not None}
        creditor = pick(normalized, "credor", "empresa", "instituicao", "nome_credor", "parceiro", "razao_social")
        amount = pick(normalized, "valor_atual", "valor_divida", "valor_total", "valor", "saldo", "saldo_devedor", "valor_negociado")
        if not creditor or not amount:
            continue
        contract = pick(normalized, "contrato", "numero_contrato", "id_contrato", "protocolo", "codigo")
        due_date = parse_date(pick(normalized, "vencimento", "data_vencimento", "data_de_vencimento", "data_negativacao", "data"))
        status = pick(normalized, "status", "situacao", "situacao_divida") or "Importada"
        debt_type = infer_type(normalized, creditor)
        initial_balance = parse_money(amount)
        paid_amount = parse_money(pick(normalized, "valor_pago", "pago", "abatimento"))
        minimum_payment = parse_money(pick(normalized, "parcela", "parcela_minima", "valor_parcela", "entrada"))
        rate = parse_percent(pick(normalized, "juros", "taxa_juros", "juros_mensal"))
        notes_parts = [
            f"Status Serasa: {status}",
            f"Contrato: {contract}" if contract else "",
            pick(normalized, "observacao", "descricao", "detalhe", "produto"),
        ]
        notes = " | ".join(part for part in notes_parts if part)
        external_id = stable_id(creditor, contract, amount, due_date or "", status)
        debts.append(
            SerasaDebt(
                creditor=creditor,
                debt_type=debt_type,
                initial_balance=initial_balance,
                paid_amount=paid_amount,
                monthly_interest_rate=rate,
                minimum_payment=minimum_payment,
                due_date=due_date,
                status=status,
                contract=contract,
                notes=notes,
                external_id=external_id,
            )
        )
    return debts


def pick(row: dict[str, str], *names: str) -> str:
    for name in names:
        if row.get(name):
            return row[name]
    contains = {
        "credor": ["credor", "empresa", "instituicao"],
        "valor": ["valor", "saldo", "divida"],
        "vencimento": ["vencimento", "data"],
    }
    for name in names:
        for key, value in row.items():
            if any(fragment in key for fragment in contains.get(name, [name])) and value:
                return value
    return ""


def parse_money(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    text = re.sub(r"[^0-9,.-]", "", text)
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return abs(float(text))
    except ValueError:
        return 0.0


def parse_percent(value: str) -> float:
    return parse_money(value)


def parse_date(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            pass
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        try:
            return datetime.strptime(digits, "%d%m%Y").date().isoformat()
        except ValueError:
            return None
    return None


def infer_type(row: dict[str, str], creditor: str) -> str:
    text = " ".join([creditor, *row.values()]).lower()
    if "cartao" in text or "cartão" in text:
        return "Cartao"
    if "financiamento" in text:
        return "Financiamento"
    if "parcel" in text:
        return "Parcelamento"
    if "emprest" in text:
        return "Emprestimo"
    return "Serasa"


def stable_id(*parts: str) -> str:
    payload = "|".join(str(part or "").strip().lower() for part in parts)
    return "serasa:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
