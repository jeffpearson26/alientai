"""Inventory research reports and fail closed on non-reproducible promotion evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _artifact_hashes(report: Mapping[str, Any]) -> list[str]:
    artifacts = report.get("input_artifacts")
    if not isinstance(artifacts, Mapping):
        return []
    return sorted(str(value) for key, value in artifacts.items() if key.endswith("_sha256") and value)


def _gates(report: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    gate = report.get("rare_signal_gate")
    if isinstance(gate, Mapping):
        yield gate
    results = report.get("results")
    if isinstance(results, list):
        for result in results:
            if isinstance(result, Mapping) and isinstance(result.get("rare_signal_gate"), Mapping):
                yield result["rare_signal_gate"]


def audit_paths(paths: Iterable[Path]) -> dict[str, Any]:
    reports = []
    passes_without_reproducibility = []
    reproducible_passes = []
    for path in sorted(paths):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(parsed, Mapping):
            continue
        hashes = _artifact_hashes(parsed)
        gates = [str(gate.get("status") or "") for gate in _gates(parsed)]
        item = {"report": path.name, "artifact_hash_count": len(hashes), "gates": gates}
        reports.append(item)
        if "RESEARCH_PASS" in gates:
            if hashes:
                reproducible_passes.append(item)
            else:
                passes_without_reproducibility.append(item)
    return {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "promotion_authorized": False,
        "reports_scanned": len(reports),
        "reports_with_rare_signal_gate": sum(bool(item["gates"]) for item in reports),
        "reproducible_historical_passes": reproducible_passes,
        "nonreproducible_historical_passes": passes_without_reproducibility,
        "warning": "A reproducible historical pass is still insufficient for paper trading; prospective shadow evidence and Jeff's separate review remain mandatory.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_paths(args.reports_dir.glob("*.json"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
