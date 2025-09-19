#!/usr/bin/env python3
"""Setup DB tables and test data for extraction testing."""

from ct_scraper.database import Base, engine, session_scope
from ct_scraper.models import Case, Party

# Create all tables
Base.metadata.create_all(engine)
print("Tables created.")

with session_scope() as session:
    # Add test case
    case = Case(
        docket_no="AANCV156018160S",
        town="Bridgeport",
        case_type="Civil",
        court_location="Superior Court",
        property_address="Test Property",
        list_type="Trial List",
        trial_list_claim="Test Claim",
        last_action_date="2025-09-19"
    )
    session.add(case)
    session.flush()  # Get ID

    # Add placeholder party
    party = Party(
        case_id=case.id,
        docket_no=case.docket_no,
        role="D-01",
        name="Placeholder Defendant",
        attorney="",
        mailing_address="Placeholder Address",
        file_date=""
    )
    session.add(party)
    session.commit()

print("Test case and party added for AANCV156018160S.")
print("Run: python scripts/pdf_llm_extract.py --docket AANCV156018160S --out-csv /tmp/test_extract.csv")