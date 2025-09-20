"""Database migration script to rename attorney_address to mailing_address."""

import sqlite3
from pathlib import Path

def migrate_database(db_path: Path) -> None:
    """Rename attorney_address column to mailing_address in parties table."""
    if not db_path.exists():
        print(f"Database file {db_path} does not exist.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if the attorney_address column exists
    cursor.execute("PRAGMA table_info(parties)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'attorney_address' in columns:
        print("Renaming attorney_address column to mailing_address...")
        
        # SQLite doesn't support direct column rename, so we need to:
        # 1. Create a new table with the correct schema
        # 2. Copy data from old table
        # 3. Drop old table
        # 4. Rename new table
        
        # Create temporary table with correct column name
        cursor.execute("""
        CREATE TABLE parties_temp (
            id INTEGER PRIMARY KEY,
            case_id INTEGER,
            docket_no TEXT,
            role TEXT,
            name TEXT,
            attorney TEXT,
            mailing_address TEXT,
            file_date TEXT,
            FOREIGN KEY(case_id) REFERENCES cases(id),
            UNIQUE(case_id, role, name)
        )
        """)
        
        # Copy data from old table to new table
        cursor.execute("""
        INSERT INTO parties_temp (id, case_id, docket_no, role, name, attorney, mailing_address, file_date)
        SELECT id, case_id, docket_no, role, name, attorney, attorney_address, file_date
        FROM parties
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE parties")
        
        # Rename new table
        cursor.execute("ALTER TABLE parties_temp RENAME TO parties")
        
        # Recreate indexes and constraints
        cursor.execute("CREATE INDEX ix_parties_case_id ON parties (case_id)")
        cursor.execute("CREATE INDEX ix_parties_docket_no ON parties (docket_no)")
        
        conn.commit()
        print("Successfully renamed attorney_address to mailing_address")
    else:
        print("attorney_address column not found in parties table. No migration needed.")
    
    conn.close()

if __name__ == "__main__":
    # Default database path - adjust as needed for your environment
    default_db_path = Path(__file__).parent.parent / "data" / "ct_scraper.db"
    
    # You can also specify a custom path via command line
    import sys
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    else:
        db_path = default_db_path
    
    print(f"Migrating database: {db_path}")
    migrate_database(db_path)