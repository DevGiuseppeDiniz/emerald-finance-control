from __future__ import annotations

import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emerald_finance.database import add_transaction, connect, find_account_for_description, get_summary
from emerald_finance.ofx import parse_ofx


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        summary = get_summary(conn)
        assert round(summary.balance, 2) == 3652.84
        assert round(summary.open_debt, 2) == 11500.00

        sample = """
        <OFX><BANKTRANLIST>
        <STMTTRN><DTPOSTED>20260621120000<TRNAMT>-12.34<FITID>abc123<MEMO>UBER TESTE</STMTTRN>
        </BANKTRANLIST></OFX>
        """
        transactions = parse_ofx(sample)
        assert len(transactions) == 1
        account_id = find_account_for_description(conn, transactions[0].description)
        assert account_id is not None
        assert add_transaction(
            conn,
            transactions[0].posted_at,
            transactions[0].description,
            transactions[0].amount,
            account_id,
            "OFX",
            transactions[0].external_id,
        )
        assert not add_transaction(
            conn,
            transactions[0].posted_at,
            transactions[0].description,
            transactions[0].amount,
            account_id,
            "OFX",
            transactions[0].external_id,
        )
        conn.close()
    print("smoke-test-ok")


if __name__ == "__main__":
    main()
