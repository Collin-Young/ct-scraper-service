from pathlib import Path
path = Path('ct_scraper/scrape_cases.py')
text = path.read_text()
text = text.replace("f\"//table[@id='ctl00_ContentPlaceHolder1_gvPropertyResults']//span[text()='${next_page_num}']\"", "f\"//table[@id='ctl00_ContentPlaceHolder1_gvPropertyResults']//span[text()='{next_page_num}']\"")
path.write_text(text)
