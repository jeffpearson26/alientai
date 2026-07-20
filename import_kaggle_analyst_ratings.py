from __future__ import annotations

"""Import the free 2009-2020 Kaggle/Benzinga headline history safely.

The public dataset is useful research material, but it is not an official Benzinga
event feed.  This importer therefore keeps the provider distinct, preserves source
wording, never invents a prior rating, and applies a conservative next-day timestamp
to date-only rows.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import shutil
import zipfile
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Tuple

import requests

from alientai_v2.data.analyst_ratings import normalize_event


ROOT = Path(__file__).resolve().parent
DATASET_REF = "miguelaenlle/massive-stock-news-analysis-db-for-nlpbacktests"
DATASET_PAGE = f"https://www.kaggle.com/datasets/{DATASET_REF}"
PROCESSED_MIRROR = (
    "https://huggingface.co/datasets/starve/ticker/resolve/main/"
    "analyst_ratings_processed.csv"
)
DEFAULT_ARCHIVE_DIR = ROOT / "data_v2" / "analyst_ratings_kaggle_history"
PROVIDER = "KAGGLE_BENZINGA_HEADLINE"
EXPECTED_PROCESSED_MIN_ROWS = 1_300_000

_TARGET_CHANGE_RE = re.compile(
    r"(?:,\s*)?(?P<target_action>Raises|Lowers|Cuts|Boosts|Sets)\s+(?:Price\s+Target|PT)"
    r"(?:\s+From\s+\$?(?P<old>[0-9][0-9,.]*))?\s+to\s+\$?(?P<new>[0-9][0-9,.]*)"
    r"(?:\s.*)?$",
    re.IGNORECASE,
)
_TARGET_ANNOUNCE_RE = re.compile(
    r"(?:,\s*)?Announces\s+(?:"
    r"\$?(?P<new_first>[0-9][0-9,.]*)\s+(?:Price\s+Target|PT)"
    r"|(?:Price\s+Target|PT)(?:\s+(?:of|at|to))?\s+\$?(?P<new_second>[0-9][0-9,.]*)"
    r")(?:\s.*)?$",
    re.IGNORECASE,
)
_FROM_TO_RE = re.compile(
    r"^(?P<firm>.+?)\s+(?P<action>Upgrades|Downgrades)\s+(?P<company>.+?)\s+"
    r"from\s+(?P<old>.+?)\s+to\s+(?P<new>.+)$",
    re.IGNORECASE,
)
_MAINTAIN_RE = re.compile(
    r"^(?P<firm>.+?)\s+(?P<action>Maintains|Reiterates)\s+(?P<new>.+?)\s+on\s+(?P<company>.+)$",
    re.IGNORECASE,
)
_CHANGE_TO_RE = re.compile(
    r"^(?P<firm>.+?)\s+(?P<action>Upgrades|Downgrades)\s+(?P<company>.+?)\s+to\s+(?P<new>.+)$",
    re.IGNORECASE,
)
_INITIATE_RE = re.compile(
    r"^(?P<firm>.+?)\s+(?P<action>Initiates)(?:\s+Coverage)?\s+On\s+(?P<company>.+?)\s+"
    r"(?:with|at)\s+(?P<new>.+?)(?:\s+Rating)?$",
    re.IGNORECASE,
)
_VALID_TICKER_RE = re.compile(r"^[A-Z0-9.^-]{1,16}$")
_CREDIT_RATING_RE = re.compile(
    r"^(?:AAA|AA|A|BBB|BB|B|CCC|CC|C|RD|SD|D)[+-]?$"
    r"|^(?:Aaa|Aa[123]|A[123]|Baa[123]|Ba[123]|B[123]|Caa[123]|Ca|C)$"
)
_CREDIT_FIRM_RE = re.compile(r"^(?:S&P|Moody|Fitch|DBRS|A\.M\. Best)\b", re.IGNORECASE)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_rating(value: Any) -> str:
    text = _clean_text(value).strip(" ,.;:-")
    text = re.sub(r"\s+Rating$", "", text, flags=re.IGNORECASE).strip()
    return text


def _number(value: Any) -> float | None:
    raw = _clean_text(value).replace(",", "").replace("$", "")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _extract_targets(headline: str) -> Tuple[str, float | None, float | None, str]:
    for pattern in (_TARGET_CHANGE_RE, _TARGET_ANNOUNCE_RE):
        match = pattern.search(headline)
        if match:
            old_target = _number(match.groupdict().get("old"))
            new_target = _number(
                match.groupdict().get("new")
                or match.groupdict().get("new_first")
                or match.groupdict().get("new_second")
            )
            return headline[: match.start()].rstrip(" ,"), old_target, new_target, _clean_text(
                match.groupdict().get("target_action") or "Announces"
            )
    return headline, None, None, ""


def _credit_label(value: str) -> bool:
    core = value.split(";", 1)[0].strip()
    return bool(_CREDIT_RATING_RE.fullmatch(core))


def parse_rating_headline(headline: Any) -> Dict[str, Any] | None:
    """Extract only high-specificity, single-company analyst actions."""
    original = _clean_text(headline)
    if not original or len(original) > 600:
        return None
    core, old_target, new_target, target_action = _extract_targets(original)
    match = None
    quality = "action_and_new_rating"
    for pattern in (_FROM_TO_RE, _MAINTAIN_RE, _CHANGE_TO_RE, _INITIATE_RE):
        match = pattern.match(core)
        if match:
            if pattern is _FROM_TO_RE:
                quality = "explicit_old_to_new"
            break
    if not match:
        return None
    values = match.groupdict()
    firm = _clean_text(values.get("firm"))
    action = _clean_text(values.get("action"))
    old_rating = _clean_rating(values.get("old"))
    new_rating = _clean_rating(values.get("new"))
    company = _clean_text(values.get("company"))
    if not firm or not action or not new_rating or not company:
        return None
    if len(firm) > 100 or len(old_rating) > 80 or len(new_rating) > 80:
        return None
    for rating in (old_rating, new_rating):
        if rating and (
            not re.search(r"[A-Za-z]", rating)
            or "$" in rating
            or re.search(r"\b(?:price\s+target|PT)\b", rating, flags=re.IGNORECASE)
        ):
            return None
    forbidden = ("price target", "biggest movers", "stocks moving", "top upgrades")
    if any(term in new_rating.casefold() for term in forbidden):
        return None
    if "outlook" in original.casefold():
        return None
    if (old_rating and _credit_label(old_rating) and _credit_label(new_rating)) or (
        _CREDIT_FIRM_RE.search(firm) and _credit_label(new_rating)
    ):
        return None
    return {
        "analyst_firm": firm,
        "action": action,
        "old_rating": old_rating,
        "new_rating": new_rating,
        "company_from_headline": company,
        "old_price_target": old_target,
        "new_price_target": new_target,
        "price_target_action": target_action,
        "parse_quality": quality,
    }


def safe_timestamp(value: Any) -> Tuple[str, str]:
    """Return a leakage-safe UTC timestamp and the applied timing policy."""
    raw = _clean_text(value)
    if not raw:
        raise ValueError("missing source timestamp")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        source_day = date.fromisoformat(raw)
        conservative = datetime.combine(
            source_day + timedelta(days=1), time(23, 59, 59), tzinfo=timezone.utc
        )
        return conservative.isoformat().replace("+00:00", "Z"), "date_only_next_calendar_day_end"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid source timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp without timezone is unsafe")
    return (
        parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_offset_timestamp",
    )


def _first(row: Mapping[str | None, Any], *names: str) -> str:
    folded = {str(key or "").strip().casefold(): value for key, value in row.items()}
    for name in names:
        value = _clean_text(folded.get(name.casefold()))
        if value:
            return value
    return ""


def normalize_kaggle_row(row: Mapping[str | None, Any]) -> Dict[str, Any] | None:
    headline = _first(row, "title", "headline")
    parsed = parse_rating_headline(headline)
    if not parsed:
        return None
    ticker = _first(row, "stock", "ticker", "symbol").upper()
    if not _VALID_TICKER_RE.fullmatch(ticker):
        raise ValueError("invalid or missing ticker")
    raw_timestamp = _first(row, "date", "publisheddate", "published_at", "timestamp")
    announced, timestamp_policy = safe_timestamp(raw_timestamp)
    source_url = _first(row, "url", "newsurl") or DATASET_PAGE
    row_id = _first(row, "", "unnamed: 0", "index", "id")
    if not row_id:
        row_id = hashlib.sha256(
            f"{ticker}|{raw_timestamp}|{headline}".encode("utf-8")
        ).hexdigest()
    payload = {
        "dataset_ref": DATASET_REF,
        "dataset_page": DATASET_PAGE,
        "headline": headline,
        "source_timestamp_original": raw_timestamp,
        "timestamp_policy": timestamp_policy,
        "parse_quality": parsed["parse_quality"],
        "company_from_headline": parsed["company_from_headline"],
        "price_target_action": parsed["price_target_action"],
        "unofficial_derived_source": True,
        "prior_rating_inferred": False,
    }
    return normalize_event(
        provider=PROVIDER,
        ticker=ticker,
        announcement_timestamp=announced,
        analyst_firm=parsed["analyst_firm"],
        action=parsed["action"],
        old_rating=parsed["old_rating"],
        new_rating=parsed["new_rating"],
        old_price_target=parsed["old_price_target"],
        new_price_target=parsed["new_price_target"],
        source_id=f"{DATASET_REF}:{row_id}",
        source_url=source_url,
        raw_payload=payload,
    )


def iter_source_rows(path: Path) -> Iterator[Tuple[str, Dict[str | None, Any]]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            candidates = [name for name in archive.namelist() if name.casefold().endswith(".csv")]
            if not candidates:
                raise ValueError("archive contains no CSV file")
            candidates.sort(
                key=lambda name: (
                    "analyst_ratings_processed" not in name.casefold(),
                    "raw_analyst_ratings" not in name.casefold(),
                    name.casefold(),
                )
            )
            member = candidates[0]
            with archive.open(member) as binary:
                with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                    for row in csv.DictReader(text):
                        yield member, dict(row)
        return
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            yield path.name, dict(row)


def file_sha256(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def download_processed_file(
    destination: Path,
    url: str = PROCESSED_MIRROR,
    minimum_free_gb: float = 5.0,
) -> Path:
    """Resumably download the public processed CSV while preserving disk reserve."""
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with requests.get(url, headers=headers, stream=True, timeout=90) as response:
        response.raise_for_status()
        append = offset > 0 and response.status_code == 206
        if offset and not append:
            offset = 0
        remaining = int(response.headers.get("content-length") or 0)
        free = shutil.disk_usage(destination.parent).free
        reserve = int(minimum_free_gb * 1024**3)
        if remaining and free - remaining < reserve:
            raise RuntimeError("download refused: minimum free-space reserve would be violated")
        mode = "ab" if append else "wb"
        with partial.open(mode) as handle:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    handle.write(block)
    partial.replace(destination)
    return destination


def download_kaggle_original(output_dir: Path, minimum_free_gb: float = 5.0) -> Path:
    """Download only the original processed CSV through Kaggle's official client."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(output_dir.parent if not output_dir.exists() else output_dir).free
    reserve = int(minimum_free_gb * 1024**3)
    if free < reserve + 1024**3:
        raise RuntimeError("Kaggle download refused: free-space reserve is too small")
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError("kagglehub is required for --download-kaggle-original") from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = kagglehub.dataset_download(
        DATASET_REF,
        path="analyst_ratings_processed.csv",
        output_dir=str(output_dir),
    )
    source = Path(downloaded)
    if source.is_dir():
        source = source / "analyst_ratings_processed.csv"
    if not source.is_file():
        raise RuntimeError("Kaggle download completed without the requested CSV")
    return source


def _semantic_event_key(row: Mapping[str, Any]) -> Tuple[Any, ...]:
    payload = row.get("raw_payload") if isinstance(row.get("raw_payload"), Mapping) else {}
    source_day = _clean_text(payload.get("source_timestamp_original"))[:10]
    return (
        row.get("ticker"),
        source_day or _clean_text(row.get("announcement_timestamp_utc"))[:10],
        _clean_text(row.get("analyst_firm")).casefold(),
        _clean_text(row.get("normalized_action")),
        _clean_text(row.get("old_rating")).casefold(),
        _clean_text(row.get("new_rating")).casefold(),
    )


def _merge_semantic_duplicate(
    current: Dict[str, Any], candidate: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool]:
    """Keep the earliest timestamp and enrich it with non-conflicting target data."""
    replaced = candidate["announcement_timestamp_utc"] < current["announcement_timestamp_utc"]
    winner, other = (candidate, current) if replaced else (current, candidate)
    winner = dict(winner)
    for field in ("old_price_target", "new_price_target"):
        if winner.get(field) is None and other.get(field) is not None:
            winner[field] = other[field]
    payload = dict(winner.get("raw_payload") or {})
    previous_count = int((current.get("raw_payload") or {}).get("semantic_duplicate_count") or 1)
    candidate_count = int((candidate.get("raw_payload") or {}).get("semantic_duplicate_count") or 1)
    payload["semantic_duplicate_count"] = previous_count + candidate_count
    source_ids = []
    for record in (current, candidate):
        record_ids = [record.get("source_id")]
        record_ids.extend((record.get("raw_payload") or {}).get("merged_source_ids") or [])
        for source_id in record_ids:
            if source_id and source_id not in source_ids:
                source_ids.append(source_id)
    payload["merged_source_ids"] = source_ids[:20]
    winner["raw_payload"] = payload
    return winner, replaced


def import_history(
    source: Path,
    output: Path,
    *,
    require_explicit_old_rating: bool = False,
    minimum_accepted: int = 1,
    minimum_source_rows: int = 1,
    max_rows: int | None = None,
) -> Dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    manifest_path = output.with_name(output.name + ".manifest.json")
    counts: Counter[str] = Counter()
    accepted_by_key: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    member_names = set()
    try:
        for member, row in iter_source_rows(source):
            member_names.add(member)
            counts["rows_seen"] += 1
            if max_rows is not None and counts["rows_seen"] > max_rows:
                break
            try:
                normalized = normalize_kaggle_row(row)
            except ValueError:
                counts["rejected_invalid_required_field"] += 1
                continue
            if normalized is None:
                counts["rejected_not_single_rating_event"] += 1
                continue
            quality = normalized["raw_payload"]["parse_quality"]
            if require_explicit_old_rating and quality != "explicit_old_to_new":
                counts["rejected_missing_explicit_old_rating"] += 1
                continue
            counts["parsed_candidates"] += 1
            key = _semantic_event_key(normalized)
            current = accepted_by_key.get(key)
            if current is None:
                accepted_by_key[key] = normalized
            else:
                counts["rejected_semantic_duplicate"] += 1
                merged, replaced = _merge_semantic_duplicate(current, normalized)
                accepted_by_key[key] = merged
                if replaced:
                    counts["semantic_duplicate_earlier_timestamp_replacements"] += 1
        counts["accepted"] = len(accepted_by_key)
        for normalized in accepted_by_key.values():
            quality = normalized["raw_payload"]["parse_quality"]
            counts[f"accepted_{quality}"] += 1
        if counts["rows_seen"] < minimum_source_rows:
            raise RuntimeError(
                f"source appears truncated: saw {counts['rows_seen']} rows, "
                f"expected at least {minimum_source_rows}"
            )
        if counts["accepted"] < minimum_accepted:
            raise RuntimeError(
                f"import refused: accepted {counts['accepted']} rows, below minimum {minimum_accepted}"
            )
        with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6, newline="\n") as handle:
            for normalized in sorted(
                accepted_by_key.values(),
                key=lambda item: (item["announcement_timestamp_utc"], item["event_id"]),
            ):
                handle.write(json.dumps({"normalized": normalized}, separators=(",", ":")) + "\n")
        temporary.replace(output)
        status = "complete"
    except Exception:
        temporary.unlink(missing_ok=True)
        status = "failed_closed"
        raise
    finally:
        manifest = {
            "status": status,
            "dataset_ref": DATASET_REF,
            "source_path": str(source.resolve()),
            "source_members": sorted(member_names),
            "source_size_bytes": source.stat().st_size if source.exists() else None,
            "source_sha256": file_sha256(source) if source.exists() else None,
            "output_path": str(output.resolve()),
            "require_explicit_old_rating": bool(require_explicit_old_rating),
            "minimum_accepted": int(minimum_accepted),
            "minimum_source_rows": int(minimum_source_rows),
            "counts": dict(sorted(counts.items())),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path)
    source_group.add_argument(
        "--download-processed",
        action="store_true",
        help="Download the public mirror; the completeness guard rejects truncated copies.",
    )
    source_group.add_argument("--download-kaggle-original", action="store_true")
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_ARCHIVE_DIR / "analyst_ratings_processed.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ARCHIVE_DIR / "parsed_rating_events.jsonl.gz",
    )
    parser.add_argument("--download-url", default=PROCESSED_MIRROR)
    parser.add_argument(
        "--kaggle-output-dir",
        type=Path,
        default=DEFAULT_ARCHIVE_DIR / "original_kaggle",
    )
    parser.add_argument("--minimum-free-gb", type=float, default=5.0)
    parser.add_argument("--minimum-accepted", type=int, default=1)
    parser.add_argument(
        "--minimum-source-rows",
        type=int,
        default=EXPECTED_PROCESSED_MIN_ROWS,
        help="Completeness guard; lower only for an intentional sample run.",
    )
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--require-explicit-old-rating", action="store_true")
    args = parser.parse_args()
    source = args.input
    if args.download_processed:
        source = download_processed_file(args.cache, args.download_url, args.minimum_free_gb)
    elif args.download_kaggle_original:
        source = download_kaggle_original(args.kaggle_output_dir, args.minimum_free_gb)
    result = import_history(
        source,
        args.output,
        require_explicit_old_rating=args.require_explicit_old_rating,
        minimum_accepted=args.minimum_accepted,
        minimum_source_rows=args.minimum_source_rows,
        max_rows=args.max_rows,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
