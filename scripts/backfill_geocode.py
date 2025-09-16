"""Backfill latitude/longitude for cases."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ct_scraper.geocode import geocode_address

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ct_scraper.db"

def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, property_address, town FROM cases WHERE latitude IS NULL OR longitude IS NULL"
    ).fetchall()
    total = len(rows)
    print(f"Cases needing geocode: {total}")
    updated = 0
    for idx, (case_id, address, town) in enumerate(rows, 1):
        if not address:
            continue
        coords = geocode_address(address, town)
        if coords:
            cur.execute(
                "UPDATE cases SET latitude = ?, longitude = ? WHERE id = ?",
                (coords[0], coords[1], case_id),
            )
            conn.commit()
            updated += 1
        if idx % 50 == 0:
            print(f"Processed {idx}/{total}")
    print(f"Updated {updated} cases")
    conn.close()

if __name__ == "__main__":
    main()
