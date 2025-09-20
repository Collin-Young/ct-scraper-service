#!/usr/bin/env python3
"""Extract defendant names and mailing addresses from SUMMONS PDFs using an LLM."""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import logging
import os
import pathlib
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from dotenv import load_dotenv
load_dotenv()

import pdfplumber
import requests
from sqlalchemy import select

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ct_scraper.database import session_scope
from ct_scraper.models import Case, Party

MODEL = "google/gemini-flash-1.5"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")
RATE_LIMIT_PER_MIN = 45

BASE_DIR = PROJECT_ROOT
PDF_DIR = BASE_DIR / "downloads_ct_summons" / "pdfs"
DEBUG_DIR = BASE_DIR / "downloads_ct_summons" / "debug_parties_pages"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

DETECT_SYSTEM_PROMPT = """You are a meticulous court-document triager. Your job is to decide whether a PDF page from a Connecticut “SUMMONS – CIVIL” packet is the Parties page that contains the Parties table.

The Parties page almost always has these cues:
• A table header like: “Name (Last, First, Middle Initial) and address of each party (Number; street; P.O. Box; town; state; zip; country, if not USA)”.
• Role labels in the leftmost column: “First plaintiff”, “Additional plaintiff”, “First defendant”, “Additional defendant”.
• Short role codes at the far right such as “P-01, P-02, D-01, D-02”.
• A totals strip near the bottom: “Total number of plaintiffs: <n> Total number of defendants: <n>”.
• Often followed immediately by “Notice to each defendant”.

Negative cues (do NOT call these Parties pages):
• Foreclosure mediation flyers, ADA notices, “You are being sued” one-pagers without the Parties table, appearance forms (JD-CL-12), or anything without those role labels or totals strip.

Decision rubric:
Score the page from 0–100.
• +40 if the Parties table header text is visible.
• +20 if role labels (First/Additional plaintiff/defendant) are visible.
• +20 if “Total number of plaintiffs/defendants” strip is visible.
• +10 if D-/P- codes (e.g., D-01) are visible at the row ends.
• +10 if “Notice to each defendant” appears directly below.

Return STRICT JSON ONLY (no prose, no markdown, no code blocks or ```json fences) with this schema:
{
"is_parties_page": true|false,
"confidence": 0–100,
"signals": ["short reasons found"],
"page_index": <int>, // the 0-based page number you were given
"region_hint": "top|middle|bottom|full" // best guess where the table sits
}"""

DETECT_USER_TEMPLATE = """Docket: {docket}\nPage index: {page_index}\nReview the supplied page image and follow the rubric above. Return only the JSON schema described.\n"""

EXTRACT_SYSTEM_PROMPT = """You are a meticulous data extractor.\n\nYou will be shown an image of a CONN. Superior Court form: SUMMONS - CIVIL.\nFind the table labeled \"Parties\". Extract ONLY rows marked \"First defendant\" or \"Additional defendant\".\nEach defendant row has:\n  - a \"Name:\" line with the full defendant name (individual or entity)\n  - an \"Address:\" line with street, city, state, ZIP (sometimes includes c/o agent text)\n\nRules:\n- Ignore plaintiffs entirely.\n- Ignore handwritten scribbles.\n- Keep entity suffixes (LLC, Inc., etc.).\n- Keep \"c/o Agent for Service\" text as part of the address if present.\n- Return STRICT JSON matching the schema below and nothing else.\n"""

EXTRACT_USER_TEMPLATE = """Return ONLY this JSON:\n{\n  \"docket\": \"<string docket from file name or empty>\",\n  \"defendants\": [\n    {\"name\": \"<string>\", \"address\": \"<string>\"}\n  ]\n}\nNotes:\n- If you cannot locate the Parties table, return an empty list for \"defendants\".\n- Do NOT include plaintiffs.\n- Do NOT add extra keys.\n- Do NOT include comments or markdown.\nDocket (from file): \"{docket}\"\n"""

JSON_FENCE_RE = re.compile(r'```(?:json)?\s*\n?|\n?\s*```', re.MULTILINE | re.DOTALL)
MAX_JSON_LOG_LEN = 200


@dataclass
class DetectionOutcome:
    is_parties_page: bool
    confidence: int
    page_index: int
    region_hint: str
    signals: List[str]


@dataclass
class MatchOutcome:
    name: str
    address: str
    status: str
    matched_party_name: str = ""
    previous_address: str = ""
    stored_address: str = ""


def next_defendant_role(existing_roles: set[str]) -> str:
    current = 1
    while True:
        role = f"D-{current:02d}"
        if role.upper() not in existing_roles:
            existing_roles.add(role.upper())
            return role
        current += 1


def safe_parse_json(content: str, *, context: str) -> Dict[str, Any]:
    if not content:
        logging.warning("LLM returned empty response during %s", context)
        return {}
    # Remove entire ```json block if present
    cleaned = re.sub(r'```(?:json)?\s*\n(.*?)\n\s*```', r'\1', content, flags=re.DOTALL | re.MULTILINE)
    # Fallback stripping for opening/closing fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
    # Strip whitespace and remove empty lines
    cleaned = cleaned.strip()
    cleaned = '\n'.join(line.strip() for line in cleaned.splitlines() if line.strip())
    cleaned = cleaned.strip()
    if not cleaned:
        logging.warning("LLM returned no JSON content during %s", context)
        return {}
    try:
        parsed = json.loads(cleaned)
        return parsed
    except json.JSONDecodeError as e:
        # Log the error with cleaned content for debugging
        snippet = cleaned[:MAX_JSON_LOG_LEN] + '...' if len(cleaned) > MAX_JSON_LOG_LEN else cleaned
        logging.warning("Failed to parse JSON during %s: %s - Content: %r", context, e, snippet)
        return {}


class LLMClient:
    """Thin wrapper around the OpenRouter chat completion endpoint."""

    def __init__(self, model: str, api_url: str, api_key: str, rate_limit_per_min: int) -> None:
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")
        self.model = model
        self.api_url = api_url
        self.api_key = api_key
        self.interval = 60.0 / max(rate_limit_per_min, 1)
        self.last_call = 0.0

    def chat(self, messages: List[Dict[str, Any]], *, max_tokens: int = 600, temperature: float = 0.0) -> str:
        now = time.time()
        wait = self.interval - (now - self.last_call)
        if wait > 0:
            time.sleep(wait)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://local",
            "X-Title": "CT Summons Parties Extractor",
            "Content-Type": "application/json",
        }
        response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=90)
        self.last_call = time.time()
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text[:400]}")
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response: {json.dumps(data)[:600]}") from exc


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_str_list(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if item]


def encode_png(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def iter_pdf_page_images(pdf_path: pathlib.Path, dpi: int) -> Iterable[Tuple[int, bytes]]:
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages):
            image = page.to_image(resolution=dpi).original.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            yield index, buffer.getvalue()


def detect_parties_page(client: LLMClient, image_b64: str, docket: str, page_index: int) -> DetectionOutcome:
    user_text = DETECT_USER_TEMPLATE.format(docket=docket, page_index=page_index)
    messages = [
        {"role": "system", "content": DETECT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        },
    ]
    try:
        content = client.chat(messages, max_tokens=1000)
    except Exception as exc:
        logging.warning("Detection request failed for %s page %s: %s", docket, page_index, exc)
        return DetectionOutcome(False, 0, page_index, "full", [])

    data = safe_parse_json(content, context=f"parties detection docket={docket} page={page_index}")
    if not data:
        return DetectionOutcome(False, 0, page_index, "full", [])

    return DetectionOutcome(
        is_parties_page=bool(data.get("is_parties_page")),
        confidence=to_int(data.get("confidence"), 0),
        page_index=to_int(data.get("page_index"), page_index),
        region_hint=str(data.get("region_hint") or "full"),
        signals=to_str_list(data.get("signals", [])),
    )


def extract_defendants(client: LLMClient, image_b64: str, docket: str) -> Tuple[str, List[Dict[str, str]]]:
    user_text = EXTRACT_USER_TEMPLATE.replace("{docket}", docket)
    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        },
    ]
    try:
        content = client.chat(messages, max_tokens=1000)
    except Exception as exc:
        logging.warning("Extraction request failed for %s: %s", docket, exc)
        return docket, []

    data = safe_parse_json(content, context=f"defendant extraction docket={docket}")
    if not data:
        return docket, []

    docket_value = str(data.get("docket") or docket)
    defendants: List[Dict[str, str]] = []
    for entry in data.get("defendants", []) or []:
        name = str(entry.get("name", "")).strip()
        address = str(entry.get("address", "")).strip()
        defendants.append({"name": name, "address": address})
    return docket_value, defendants


def update_defendant_addresses(
    docket: str,
    defendants: List[Dict[str, str]],
    *,
    apply_updates: bool,
) -> Tuple[bool, int, List[Dict[str, str]], List[MatchOutcome]]:
    outcomes: List[MatchOutcome] = []
    if not defendants:
        logging.info("No defendants to process for docket %s", docket)
        return False, 0, [], outcomes
    if not apply_updates:
        for item in defendants:
            outcomes.append(
                MatchOutcome(
                    name=item.get("name", ""),
                    address=item.get("address", ""),
                    status="extracted",
                )
            )
        return False, 0, [], outcomes

    updated = 0
    unmatched: List[Dict[str, str]] = []
    clean_defendants: List[Dict[str, str]] = []
    case_found = False
    try:
        with session_scope() as session:
            case = session.scalar(select(Case).where(Case.docket_no == docket))
            if not case:
                logging.warning("No case found in database for docket %s", docket)
                unmatched.extend(defendants)
                for item in defendants:
                    outcomes.append(
                        MatchOutcome(
                            name=item.get("name", ""),
                            address=item.get("address", ""),
                            status="case_not_found",
                        )
                    )
                return False, 0, unmatched, outcomes

            case_found = True
            logging.info("Found case %s with %d total parties", docket, len(case.parties))
            parties = list(session.scalars(select(Party).where(Party.case_id == case.id).order_by(Party.id)))
            defenders = [p for p in parties if p.role and p.role.upper().startswith("D-")]
            logging.info("Found %d existing defendant parties for %s", len(defenders), docket)
            defenders.sort(key=lambda p: (p.role or "", p.id))
            role_set = {p.role.upper() for p in defenders if p.role}

            # Set docket_no on all parties if not set
            for party in parties:
                if not party.docket_no:
                    party.docket_no = docket

            for idx, item in enumerate(defendants):
                name = (item.get("name") or "").strip()
                address = (item.get("address") or "").strip()
                if name or address:
                    clean_defendants.append({"name": name, "mailing_address": address})
                try:
                    if idx < len(defenders):
                        party = defenders[idx]
                        party.docket_no = docket
                        prev_name = party.name or ""
                        prev_address = party.mailing_address or ""
                        changed = False
                        if name and name != prev_name:
                            party.name = name
                            changed = True
                        if address and address != prev_address:
                            party.mailing_address = address
                            changed = True
                        status = "updated" if changed else "unchanged"
                        if changed:
                            updated += 1
                        outcomes.append(
                            MatchOutcome(
                                name=name or prev_name,
                                address=address or prev_address,
                                status=status,
                                matched_party_name=party.name,
                                previous_address=prev_address,
                                stored_address=party.mailing_address or "",
                            )
                        )
                    else:
                        role = next_defendant_role(role_set)
                        party = Party(
                            case_id=case.id,
                            docket_no=docket,
                            role=role,
                            name=name,
                            attorney="",
                            mailing_address=address,
                            file_date="",
                        )
                        session.add(party)
                        session.flush()
                        updated += 1
                        outcomes.append(
                            MatchOutcome(
                                name=name,
                                address=address,
                                status="created",
                                matched_party_name=party.name,
                                previous_address="",
                                stored_address=party.mailing_address or "",
                            )
                        )
                except Exception as e:
                    logging.error("Error updating/creating party %d for %s: %s", idx, docket, e)
                    outcomes.append(
                        MatchOutcome(
                            name=name,
                            address=address,
                            status=f"error: {str(e)}",
                        )
                    )

            case.defendants_json = json.dumps(clean_defendants, ensure_ascii=False)
            session.commit()
            logging.info("Committed %d updates for %s", updated, docket)

    except Exception as e:
        logging.error("Database error for docket %s: %s", docket, e)
        return False, 0, list(defendants), outcomes

    return case_found, updated, unmatched, outcomes


def write_outcomes(writer: Optional[csv.DictWriter], docket: str, outcomes: List[MatchOutcome]) -> None:
    if not writer or not outcomes:
        return
    for item in outcomes:
        writer.writerow(
            {
                "docket": docket,
                "extracted_name": item.name,
                "extracted_address": item.address,
                "status": item.status,
                "matched_party_name": item.matched_party_name,
                "previous_address": item.previous_address,
                "stored_address": item.stored_address,
            }
        )


def process_pdf(
    client: LLMClient,
    pdf_path: pathlib.Path,
    *,
    dpi: int,
    save_debug: bool,
    apply_updates: bool,
    csv_writer: Optional[csv.DictWriter] = None,
) -> Tuple[bool, int]:
    docket = pdf_path.stem
    logging.info("Processing %s", docket)
    if not pdf_path.exists():
        logging.warning("PDF missing for docket %s at %s", docket, pdf_path)
        return False, 0

    best: Optional[Tuple[int, bytes, str, DetectionOutcome]] = None
    for page_index, image_bytes in iter_pdf_page_images(pdf_path, dpi):
        image_b64 = encode_png(image_bytes)
        outcome = detect_parties_page(client, image_b64, docket, page_index)
        logging.debug("Detection %s page %s -> %s (%s)", docket, page_index, outcome.is_parties_page, outcome.confidence)
        if not outcome.is_parties_page:
            continue
        if not best or outcome.confidence > best[3].confidence:
            best = (page_index, image_bytes, image_b64, outcome)

    if not best:
        logging.warning("No parties page found in %s", pdf_path.name)
        return False, 0

    page_index, image_bytes, image_b64, outcome = best
    logging.info(
        "Parties page detected for %s on page %s (confidence %s)",
        docket,
        outcome.page_index,
        outcome.confidence,
    )

    returned_docket, defendants = extract_defendants(client, image_b64, docket)
    logging.info("LLM returned %s defendant rows for %s", len(defendants), returned_docket)

    case_found = False
    updated = 0
    if apply_updates:
        # Call update_defendant_addresses, but capture case_found and updated from its logs or return
        # Since update_defendant_addresses logs them, set based on logic
        # To avoid duplication, we'll increment in main after call, but for return, assume from updated >0 implies case found
        case_found, updated, unmatched, outcomes = update_defendant_addresses(returned_docket, defendants, apply_updates=apply_updates)
        write_outcomes(csv_writer, returned_docket or docket, outcomes)
        if updated > 0:
            case_found = True # A case must have been found to be updated.
        logging.info("Updated %s defendant address records for %s", updated, returned_docket)
        if unmatched:
            logging.info("Additional defendants found for unresolved case %s: %s", returned_docket, unmatched)
    else:
        _, _, _, outcomes = update_defendant_addresses(returned_docket, defendants, apply_updates=apply_updates)
        write_outcomes(csv_writer, returned_docket or docket, outcomes)
        logging.info("Database updates skipped; captured %s defendant row(s) for %s", len(defendants), returned_docket)
        case_found = False
        updated = 0

    if save_debug:
        debug_name = f"{docket}_page{page_index:02d}_parties.png"
        debug_path = DEBUG_DIR / debug_name
        try:
            debug_path.write_bytes(image_bytes)
        except OSError as exc:
            logging.warning("Could not save debug PNG for %s: %s", docket, exc)

    return case_found, updated


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docket", action="append", help="Only process the specified docket number(s)")
    parser.add_argument("--limit", type=int, help="Process at most this many PDFs")
    parser.add_argument("--dpi", type=int, default=220, help="Render resolution for PDF pages (default: 220)")
    parser.add_argument("--skip-debug", action="store_true", help="Do not write PNG snapshots to the debug directory")
    parser.add_argument("--out-csv", help="Optional path to append extraction results as CSV")
    parser.add_argument(
        "--skip-db-update",
        action="store_true",
        help="Skip updating the database; only emit extracted rows",
    )
    return parser


def open_csv_writer(path: pathlib.Path) -> Tuple[csv.DictWriter, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    handle = path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "docket",
            "extracted_name",
            "extracted_address",
            "status",
            "matched_party_name",
            "previous_address",
            "stored_address",
        ],
    )
    if not file_exists or path.stat().st_size == 0:
        writer.writeheader()
    return writer, handle


def main() -> None:
    # Setup logging to file for server debugging
    log_dir = PROJECT_ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pdf_extract_debug.log"

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

    parser = build_arg_parser()
    args = parser.parse_args()

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if args.docket:
        wanted = {entry.strip().upper() for entry in args.docket if entry}
        pdfs = [p for p in pdfs if p.stem.upper() in wanted]
    if args.limit is not None:
        pdfs = pdfs[: args.limit]
    if not pdfs:
        logging.info("No PDFs found to process in %s", PDF_DIR)
        return

    logging.info("Starting processing of %d PDFs with apply_updates=%s", len(pdfs), not args.skip_db_update)

    client = LLMClient(MODEL, API_URL, API_KEY, RATE_LIMIT_PER_MIN)

    csv_writer: Optional[csv.DictWriter] = None
    csv_handle: Any = None
    if args.out_csv:
        csv_path = pathlib.Path(args.out_csv)
        csv_writer, csv_handle = open_csv_writer(csv_path)

    apply_updates = not args.skip_db_update
    if not apply_updates:
        logging.info("Database updates disabled; will only record extracted defendants.")

    total_processed = 0
    total_cases_found = 0
    total_updated = 0
    total_errors = 0

    for pdf_path in pdfs:
        try:
            case_found, updated = process_pdf(client, pdf_path, dpi=args.dpi, save_debug=not args.skip_debug, apply_updates=apply_updates, csv_writer=csv_writer)
            total_processed += 1
            if case_found:
                total_cases_found += 1
            total_updated += updated
        except Exception as e:
            logging.error("Error processing %s: %s", pdf_path.name, e)
            total_errors += 1

    logging.info("Processing complete: %d PDFs processed, %d cases found, %d updates, %d errors", total_processed, total_cases_found, total_updated, total_errors)

    if csv_writer:
        csv_handle.close()

    finally:
        if csv_handle:
            csv_handle.close()


if __name__ == "__main__":
    main()
