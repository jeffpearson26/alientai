from __future__ import annotations

import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from alientai_v2.data.sec_form4 import normalize_quarterly_zip


def add_tsv(archive, name, fieldnames, rows):
    from io import StringIO
    out = StringIO(newline="")
    writer = csv.DictWriter(out, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    archive.writestr(name, out.getvalue())


class SECForm4Tests(unittest.TestCase):
    def make_zip(self):
        temp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        temp.close()
        with zipfile.ZipFile(temp.name, "w") as archive:
            add_tsv(archive, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERTRADINGSYMBOL", "FILING_DATE", "ACCEPTANCE_DATETIME"], [
                {"ACCESSION_NUMBER": "0001-26-000001", "DOCUMENT_TYPE": "4", "ISSUERCIK": "123", "ISSUERTRADINGSYMBOL": "XYZ", "FILING_DATE": "2026-07-17", "ACCEPTANCE_DATETIME": "20260717183000"},
            ])
            add_tsv(archive, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME", "ISOFFICER", "ISDIRECTOR", "ISTENPERCENTOWNER", "OFFICERTITLE"], [
                {"ACCESSION_NUMBER": "0001-26-000001", "RPTOWNERCIK": "456", "RPTOWNERNAME": "JANE DOE", "ISOFFICER": "1", "ISDIRECTOR": "0", "ISTENPERCENTOWNER": "0", "OFFICERTITLE": "CFO"},
            ])
            fields = ["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "TRANS_DATE", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "SHRS_OWND_FOLWNG_TRANS", "DIRECT_INDIRECT_OWNERSHIP"]
            add_tsv(archive, "NONDERIV_TRANS.tsv", fields, [
                {"ACCESSION_NUMBER": "0001-26-000001", "NONDERIV_TRANS_SK": "1", "TRANS_DATE": "2026-07-16", "TRANS_CODE": "P", "TRANS_ACQUIRED_DISP_CD": "A", "TRANS_SHARES": "1000", "TRANS_PRICEPERSHARE": "25.50", "SHRS_OWND_FOLWNG_TRANS": "5000", "DIRECT_INDIRECT_OWNERSHIP": "D"},
                {"ACCESSION_NUMBER": "0001-26-000001", "NONDERIV_TRANS_SK": "2", "TRANS_DATE": "2026-07-16", "TRANS_CODE": "A", "TRANS_ACQUIRED_DISP_CD": "A", "TRANS_SHARES": "9000", "TRANS_PRICEPERSHARE": "1", "SHRS_OWND_FOLWNG_TRANS": "14000", "DIRECT_INDIRECT_OWNERSHIP": "D"},
                {"ACCESSION_NUMBER": "0001-26-000001", "NONDERIV_TRANS_SK": "3", "TRANS_DATE": "2026-07-16", "TRANS_CODE": "M", "TRANS_ACQUIRED_DISP_CD": "A", "TRANS_SHARES": "500", "TRANS_PRICEPERSHARE": "2", "SHRS_OWND_FOLWNG_TRANS": "14500", "DIRECT_INDIRECT_OWNERSHIP": "D"},
            ])
        return Path(temp.name)

    def test_only_code_p_purchase_is_normalized(self):
        path = self.make_zip()
        try:
            rows = normalize_quarterly_zip(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["transaction_code"], "P")
        self.assertEqual(row["total_value"], 25_500)
        self.assertEqual(row["insider_name"], "JANE DOE")
        self.assertTrue(row["is_officer"])
        self.assertEqual(row["officer_title"], "CFO")
        self.assertEqual(row["filing_timestamp_utc"], "2026-07-17T22:30:00Z")
        self.assertTrue(row["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/123/"))

    def test_transaction_id_is_stable(self):
        path = self.make_zip()
        try:
            first = normalize_quarterly_zip(path)
            second = normalize_quarterly_zip(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(first[0]["transaction_id"], second[0]["transaction_id"])

    def test_sec_quarterly_date_format_uses_conservative_availability(self):
        from alientai_v2.data.sec_form4 import _parse_acceptance
        self.assertEqual(_parse_acceptance("", "17-JUL-2026"), "2026-07-18T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
