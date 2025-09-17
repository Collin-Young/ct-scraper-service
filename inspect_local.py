from pathlib import Path
text = Path('ct_scraper/scrape_cases.py').read_text()
start = text.index("next_link =")
end = text.index("else:", start)
print(repr(text[start:end+6]))
