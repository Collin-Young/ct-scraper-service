#!/usr/bin/env python3
"""Migration script to add defendants_json column to cases table."""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ct_scraper.database import engine
from sqlalchemy import text

def add_defendants_json_column():
    """Add defendants_json column to cases table if it doesn't exist."""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                PRAGMA table_info(cases);
            """))
            columns = [row[1] for row in result.fetchall()]
            
            if 'defendants_json' not in columns:
                print("Adding defendants_json column to cases table...")
                conn.execute(text("""
                    ALTER TABLE cases ADD COLUMN defendants_json TEXT;
                """))
                conn.commit()
                print("Successfully added defendants_json column.")
            else:
                print("defendants_json column already exists.")
                
    except Exception as e:
        print(f"Error adding defendants_json column: {e}")
        return False
    
    return True

if __name__ == "__main__":
    add_defendants_json_column()