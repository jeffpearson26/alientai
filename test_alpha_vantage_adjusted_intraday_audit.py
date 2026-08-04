from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

import audit_alpha_vantage_adjusted_intraday_archive as audit
import download_alpha_vantage_adjusted_intraday_archive as archive


CSV = b"""timestamp,open,high,low,close,volume
2026-07-01 09:30:00,9.8,10.1,9.7,10.0,200
"""


def completed_archive(folder: Path) -> tuple[Path, list[str]]:
    symbols = ["AMD", "NEW"]
    contract = archive.manifest_contract(symbols, "2026-07", "2026-07")
    manifest = archive.new_manifest(contract)
    destination = archive.archive_path(folder, "AMD", "2026-07")
    destination.parent.mkdir(parents=True)
    with gzip.open(destination, "wb") as handle:
        handle.write(CSV)
    metadata = archive.validate_existing(destination, "2026-07")
    manifest["completed"] = [{
        "request": "AMD|2026-07",
        "symbol": "AMD",
        "month": "2026-07",
        "relative_path": destination.relative_to(folder).as_posix(),
        **metadata,
    }]
    manifest["unavailable"] = [{
        "request": "NEW|2026-07",
        "symbol": "NEW",
        "month": "2026-07",
        "reason": "pre-listing",
    }]
    manifest["status"] = "complete"
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder, symbols


class AdjustedIntradayAuditTests(unittest.TestCase):
    def test_complete_archive_passes_with_exact_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, symbols = completed_archive(Path(temporary))
            result = audit.audit_archive(output, symbols, "2026-07", "2026-07")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(result["validated_gzip_files"], 1)
        self.assertEqual(result["unavailable_count"], 1)

    def test_incomplete_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, symbols = completed_archive(Path(temporary))
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["status"] = "running"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "not complete"):
                audit.audit_archive(output, symbols, "2026-07", "2026-07")

    def test_tampered_file_fails_hash_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, symbols = completed_archive(Path(temporary))
            destination = archive.archive_path(output, "AMD", "2026-07")
            with gzip.open(destination, "wb") as handle:
                handle.write(CSV.replace(b",200", b",201"))
            with self.assertRaisesRegex(ValueError, "metadata mismatch"):
                audit.audit_archive(output, symbols, "2026-07", "2026-07")


if __name__ == "__main__":
    unittest.main()
