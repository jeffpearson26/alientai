from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "train_v2_transformer_20day_sp500_from_supabase.py"
TARGET = ROOT / "train_v2_transformer_5day_sp500_from_supabase.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {count}")
    return text.replace(old, new, 1)


def build_five_day_source(source: str) -> str:
    text = source
    text = replace_once(
        text,
        'BUILD = "ALIENTAI_V2_TRANSFORMER_20DAY_SP500_SUPABASE_TRAINER_V1"',
        'BUILD = "ALIENTAI_V2_TRANSFORMER_5DAY_SP500_SUPABASE_TRAINER_V1"',
        "build identifier",
    )
    text = replace_once(
        text,
        'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day_sp500_supabase_training"',
        'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_5day_sp500_supabase_training"',
        "output directory",
    )
    text = replace_once(
        text,
        'parser = argparse.ArgumentParser(description="Train V2 20-day daily transformer model.")',
        'parser = argparse.ArgumentParser(description="Train isolated V2 five-day daily Transformer model.")',
        "parser description",
    )
    text = replace_once(text, 'parser.add_argument("--horizon-days", type=int, default=20)', 'parser.add_argument("--horizon-days", type=int, default=5)', "horizon default")
    text = replace_once(text, 'parser.add_argument("--step-days", type=int, default=5)', 'parser.add_argument("--step-days", type=int, default=2)', "step default")
    text = replace_once(text, 'parser.add_argument("--split-embargo-calendar-days", type=int, default=32)', 'parser.add_argument("--split-embargo-calendar-days", type=int, default=12)', "embargo default")
    text = replace_once(text, 'parser.add_argument("--checkpoint-threshold", type=float, default=0.60)', 'parser.add_argument("--checkpoint-threshold", type=float, default=0.55)', "checkpoint default")
    text = replace_once(text, 'parser.add_argument("--checkpoint-minimum-signals", type=int, default=500)', 'parser.add_argument("--checkpoint-minimum-signals", type=int, default=1000)', "minimum signal default")
    text = replace_once(text, 'parser.add_argument("--non-overlapping-calendar-days", type=int, default=28)', 'parser.add_argument("--non-overlapping-calendar-days", type=int, default=9)', "non-overlap default")
    text = replace_once(
        text,
        '    args = parser.parse_args()\n\n    random.seed(args.seed)',
        '    args = parser.parse_args()\n\n    if args.horizon_days != 5:\n        raise ValueError("This isolated trainer is fixed to a five-trading-session horizon")\n\n    random.seed(args.seed)',
        "five-day invariant",
    )
    for old, new in (
        ("transformer_20day_sp500_model.pt", "transformer_5day_sp500_model.pt"),
        ("transformer_20day_sp500_scaler.json", "transformer_5day_sp500_scaler.json"),
        ("transformer_20day_sp500_metrics.json", "transformer_5day_sp500_metrics.json"),
        ("transformer_20day_sp500_symbol_summary.json", "transformer_5day_sp500_symbol_summary.json"),
        ("transformer_20day_sp500_config.json", "transformer_5day_sp500_config.json"),
    ):
        text = replace_once(text, old, new, old)
    return text


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    target = build_five_day_source(source)
    compile(target, str(TARGET), "exec")
    TARGET.write_text(target, encoding="utf-8")
    print(f"Created isolated five-day Transformer trainer: {TARGET.name}")


if __name__ == "__main__":
    main()
