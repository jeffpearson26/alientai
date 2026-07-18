from __future__ import annotations

"""Normalize SEC quarterly Forms 3/4/5 ZIP files into purchase-only records."""

import csv
import hashlib
import io
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping
from zoneinfo import ZoneInfo


PURCHASE_CODE = "P"


def text(row: Mapping[str, Any], *names: str) -> str:
    normalized = {str(key).upper(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.upper())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def number(row: Mapping[str, Any], *names: str) -> float:
    try:
        return float(text(row, *names).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def flag(row: Mapping[str, Any], *names: str) -> bool:
    return text(row, *names).upper() in {"1", "Y", "YES", "TRUE"}


def relationship_flag(row: Mapping[str, Any], relationship: str, *boolean_names: str) -> bool:
    if flag(row, *boolean_names):
        return True
    value = text(row, "RPTOWNER_RELATIONSHIP", "REPORTING_OWNER_RELATIONSHIP").upper()
    aliases = {
        "DIRECTOR": ("DIRECTOR",),
        "OFFICER": ("OFFICER",),
        "TEN_PERCENT_OWNER": (
            "10% OWNER", "10 PERCENT OWNER", "TEN PERCENT OWNER", "TENPERCENTOWNER",
        ),
    }
    return any(alias in value for alias in aliases[relationship])


def accession(row: Mapping[str, Any]) -> str:
    return text(row, "ACCESSION_NUMBER", "ACCESSIONNO", "ACCESSION")


def _parse_acceptance(value: str, filing_date: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 14:
        # EDGAR acceptance timestamps use U.S. Eastern wall-clock time.
        eastern = datetime.strptime(digits[:14], "%Y%m%d%H%M%S").replace(
            tzinfo=ZoneInfo("America/New_York")
        )
        return eastern.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    # Quarterly files expose filing date but not acceptance time.  Make such
    # rows visible at noon UTC on the next calendar day, safely after any SEC
    # acceptance on the reported filing date.
    filed = _parse_sec_date(filing_date)
    if filed:
        dt = datetime.fromisoformat(filed).replace(tzinfo=timezone.utc) + timedelta(days=1, hours=12)
        return dt.isoformat().replace("+00:00", "Z")
    return ""


def _parse_sec_date(value: Any) -> str:
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _read_table(archive: zipfile.ZipFile, tokens: Iterable[str]) -> List[Dict[str, str]]:
    wanted = tuple(token.lower() for token in tokens)
    candidates = [name for name in archive.namelist() if any(token in Path(name).name.lower() for token in wanted)]
    if not candidates:
        return []
    normalized_wanted = {"".join(ch for ch in token if ch.isalnum()) for token in wanted}

    def rank(name: str) -> tuple[int, int]:
        stem = Path(name).stem.lower()
        normalized_stem = "".join(ch for ch in stem if ch.isalnum())
        return (0 if normalized_stem in normalized_wanted else 1, len(name))

    with archive.open(sorted(candidates, key=rank)[0]) as raw:
        wrapper = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
        return list(csv.DictReader(wrapper, delimiter="\t"))


def _source_url(cik: str, accession_number: str) -> str:
    cik_digits = "".join(ch for ch in cik if ch.isdigit())
    accession_digits = "".join(ch for ch in accession_number if ch.isdigit())
    if not cik_digits or not accession_digits:
        return ""
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik_digits)}/{accession_digits}/"


def normalize_quarterly_zip(path: str | Path) -> List[Dict[str, Any]]:
    """Return normalized, deduplicated Form 4 code-P acquisitions."""
    with zipfile.ZipFile(path) as archive:
        submissions = _read_table(archive, ("submission", "sub.txt"))
        owners = _read_table(archive, ("reportingowner", "reporting_owner", "owner"))
        transactions = _read_table(archive, ("nonderiv_trans", "nonderivtrans"))

    submission_by_accession = {accession(row): row for row in submissions if accession(row)}
    owners_by_accession: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in owners:
        if accession(row):
            owners_by_accession[accession(row)].append(row)

    results: Dict[str, Dict[str, Any]] = {}
    for transaction in transactions:
        acc = accession(transaction)
        submission = submission_by_accession.get(acc, {})
        form = text(submission, "DOCUMENT_TYPE", "FORM_TYPE", "SUBMISSIONTYPE").upper()
        code = text(transaction, "TRANS_CODE", "TRANSACTION_CODE").upper()
        acquired = text(transaction, "TRANS_ACQUIRED_DISP_CD", "ACQUIRED_DISPOSED_CODE").upper()
        if form not in {"4", "4/A"} or code != PURCHASE_CODE or acquired not in {"", "A"}:
            continue
        shares = number(transaction, "TRANS_SHARES", "TRANSACTION_SHARES")
        price = number(transaction, "TRANS_PRICEPERSHARE", "TRANSACTION_PRICE_PER_SHARE")
        if shares <= 0.0 or price <= 0.0:
            continue
        issuer_cik = text(submission, "ISSUERCIK", "ISSUER_CIK")
        ticker = text(submission, "ISSUERTRADINGSYMBOL", "ISSUER_TRADING_SYMBOL").upper()
        filing_date = text(submission, "FILING_DATE", "FILED_DATE")
        available_at = _parse_acceptance(
            text(submission, "ACCEPTANCE_DATETIME", "ACCEPTANCE_TIME"), filing_date
        )
        reporting_owners = owners_by_accession.get(acc) or [{}]
        for owner in reporting_owners:
            identity = "|".join((
                acc, text(transaction, "NONDERIV_TRANS_SK", "TRANSACTION_ID"),
                text(owner, "RPTOWNERCIK", "REPORTING_OWNER_CIK"),
                text(transaction, "TRANS_DATE", "TRANSACTION_DATE"), str(shares), str(price),
            ))
            transaction_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            results[transaction_id] = {
                "transaction_id": transaction_id,
                "ticker": ticker,
                "cik": issuer_cik,
                "accession_number": acc,
                "filing_timestamp_utc": available_at,
                "available_at_utc": available_at,
                "transaction_date": _parse_sec_date(text(transaction, "TRANS_DATE", "TRANSACTION_DATE")),
                "insider_name": text(owner, "RPTOWNERNAME", "REPORTING_OWNER_NAME"),
                "officer_title": text(owner, "OFFICERTITLE", "OFFICER_TITLE", "RPTOWNER_TITLE"),
                "is_director": relationship_flag(owner, "DIRECTOR", "ISDIRECTOR", "IS_DIRECTOR"),
                "is_officer": relationship_flag(owner, "OFFICER", "ISOFFICER", "IS_OFFICER"),
                "is_ten_percent_owner": relationship_flag(
                    owner, "TEN_PERCENT_OWNER", "ISTENPERCENTOWNER", "IS_TEN_PERCENT_OWNER"
                ),
                "transaction_code": code,
                "shares": shares,
                "price": price,
                "total_value": shares * price,
                "ownership_type": text(transaction, "DIRECT_INDIRECT_OWNERSHIP", "OWNERSHIP_TYPE"),
                "shares_owned_after": number(transaction, "SHRS_OWND_FOLWNG_TRANS", "SHARES_OWNED_AFTER"),
                "is_amendment": form == "4/A",
                "supersedes_accession": "",
                "availability_precision": "acceptance_datetime" if text(submission, "ACCEPTANCE_DATETIME", "ACCEPTANCE_TIME") else "filing_date_conservative",
                "source_url": _source_url(issuer_cik, acc),
                "source": "SEC_QUARTERLY_345",
            }
    return sorted(results.values(), key=lambda row: (row["available_at_utc"], row["ticker"], row["transaction_id"]))
