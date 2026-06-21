from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emerald_finance.database import connect
from emerald_finance.postgres_sync import sync_sqlite_to_postgres


def main() -> None:
    conn = connect()
    counts = sync_sqlite_to_postgres(conn)
    conn.close()
    print("Sincronizacao concluida:")
    for table, count in counts.items():
        print(f"- {table}: {count} registro(s)")


if __name__ == "__main__":
    main()
