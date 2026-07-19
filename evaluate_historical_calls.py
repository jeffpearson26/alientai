from __future__ import annotations

import argparse
import json
from pathlib import Path

from alientai_v2.research.historical_call_evaluator import chain_path, evaluate_trade, load_chain, summarize


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    trades = []
    missing_chain_pairs = 0
    for row in read_jsonl(args.events):
        symbol = str(row.get("symbol") or "").upper()
        entry_path = chain_path(args.chains, symbol, str(row.get("market_date")))
        exit_path = chain_path(args.chains, symbol, str(row.get("future_market_date")))
        if not entry_path.exists() or not exit_path.exists():
            missing_chain_pairs += 1
            continue
        entry_chain, exit_chain = load_chain(entry_path), load_chain(exit_path)
        for strategy in ("atm_30d", "delta60_30d"):
            trade = evaluate_trade(row, entry_chain, exit_chain, strategy)
            if trade:
                trades.append(trade)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for trade in trades:
            handle.write(json.dumps(trade, sort_keys=True) + "\n")
    report = {
        "research_only": True, "execution_enabled": False,
        "warning": "Historical end-of-day bid/ask simulation; results are not evidence of executable intraday fills.",
        "missing_chain_pairs": missing_chain_pairs, "trade_rows": len(trades), "metrics": summarize(trades),
    }
    args.summary_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
