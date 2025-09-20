"""Database migration script to add docket_no column to parties table."""

import sqlite3
from pathlib import Path

def migrate_database(db_path: Path) -> None:
    """Add docket_no column to parties table if it doesn't exist."""
    if not db_path.exists():
        print(f"Database file {db_path} does not exist.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if the docket_no column exists
    cursor.execute("PRAGMA table_info(parties)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'docket_no' not in columns:
        print("Adding docket_no column to parties table...")
        
        # Add the docket_no column
        cursor.execute("ALTER TABLE parties ADD COLUMN docket_no VARCHAR(64)")
        
        # Create index on the new column
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_parties_docket_no ON parties (docket_no)")
        
        conn.commit()
        print("Successfully added docket_no column to parties table")
    else:
        print("docket_no column already exists in parties table. No migration needed.")
    
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