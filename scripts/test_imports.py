#!/usr/bin/env python3
"""Test script to verify imports work"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from ct_scraper.database import get_session
    from ct_scraper.models import Case
    from sqlalchemy.orm import Session
    print("✅ Imports successful!")
    
    # Test database connection
    with get_session() as session:
        count = session.query(Case).count()
        print(f"✅ Database connection successful! Total cases: {count}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()