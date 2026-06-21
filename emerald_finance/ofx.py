from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class OfxTransaction:
    posted_at: str
    description: str
    amount: float
    external_id: str


def _capture(block: str, tag: str) -> str:
    xml = re.search(rf"<{tag}>(.*?)</{tag}>", block, flags=re.I | re.S)
    if xml:
        return html.unescape(xml.group(1).strip())
    sgml = re.search(rf"<{tag}>([^\r\n<]+)", block, flags=re.I)
    return html.unescape(sgml.group(1).strip()) if sgml else ""


def _ofx_date(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 8:
        return ""
    return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"


def parse_ofx(text: str) -> list[OfxTransaction]:
    normalized = text.replace("\r", "")
    blocks = re.findall(r"<STMTTRN>(.*?)(?=<STMTTRN>|</BANKTRANLIST>|$)", normalized, flags=re.I | re.S)
    transactions: list[OfxTransaction] = []

    for block in blocks:
        amount_raw = _capture(block, "TRNAMT").replace(",", ".")
        try:
            amount = float(amount_raw)
        except ValueError:
            continue
        description = _capture(block, "MEMO") or _capture(block, "NAME") or _capture(block, "PAYEE") or "Lancamento OFX"
        posted_at = _ofx_date(_capture(block, "DTPOSTED") or _capture(block, "DTUSER"))
        external_id = _capture(block, "FITID") or f"{posted_at}-{description}-{amount}"
        if posted_at:
            transactions.append(OfxTransaction(posted_at, description, amount, external_id))

    return transactions
