"""Initialize MO database and populate static data."""
import json
import os
from mo_scraper.database import init_db, get_session
from mo_scraper.models import CaseType, DropdownOption


def main():
    init_db()
    session = get_session()

    # Populate case_types
    case_types_path = os.path.join('ct-scraper-service', 'mo_scraper', 'static', 'case_types.json')
    with open(case_types_path, 'r') as f:
        case_types_data = json.load(f)
    for item in case_types_data:
        if not session.query(CaseType).filter_by(name=item['type']).first():
            session.add(CaseType(name=item['type']))
    session.commit()
    print("Case types populated.")

    # Populate dropdown_options
    dropdown_path = os.path.join('ct-scraper-service', 'mo_scraper', 'static', 'dropdown_options.json')
    with open(dropdown_path, 'r') as f:
        dropdown_data = json.load(f)
    for item in dropdown_data:
        if item['text'] != "Please select...":
            if not session.query(DropdownOption).filter_by(value=item['text']).first():
                session.add(DropdownOption(category='court', value=item['text']))
    session.commit()
    print("Dropdown options populated.")

    session.close()
    print("MO DB setup complete.")


if __name__ == "__main__":
    main()