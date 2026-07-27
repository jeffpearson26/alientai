from __future__ import annotations

from pathlib import Path

from create_v2_transformer_5day_sp500_trainer import replace_once


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "train_v2_transformer_20day_sp500_from_supabase.py"
TARGET = ROOT / "train_v2_transformer_2day_sp500_from_supabase.py"


def build_two_day_source(source: str) -> str:
    text = source
    replacements = (
        (
            'BUILD = "ALIENTAI_V2_TRANSFORMER_20DAY_SP500_SUPABASE_TRAINER_V1"',
            'BUILD = "ALIENTAI_V2_TRANSFORMER_2DAY_SP500_SUPABASE_TRAINER_V1"',
            "build identifier",
        ),
        (
            'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day_sp500_supabase_training"',
            'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_2day_sp500_supabase_training"',
            "output directory",
        ),
        (
            'parser = argparse.ArgumentParser(description="Train V2 20-day daily transformer model.")',
            'parser = argparse.ArgumentParser(description="Train isolated V2 two-day daily Transformer model.")',
            "parser description",
        ),
        ('parser.add_argument("--horizon-days", type=int, default=20)', 'parser.add_argument("--horizon-days", type=int, default=2)', "horizon default"),
        ('parser.add_argument("--step-days", type=int, default=5)', 'parser.add_argument("--step-days", type=int, default=1)', "step default"),
        ('parser.add_argument("--split-embargo-calendar-days", type=int, default=32)', 'parser.add_argument("--split-embargo-calendar-days", type=int, default=12)', "embargo default"),
        ('parser.add_argument("--checkpoint-threshold", type=float, default=0.60)', 'parser.add_argument("--checkpoint-threshold", type=float, default=0.55)', "checkpoint default"),
        ('parser.add_argument("--checkpoint-minimum-signals", type=int, default=500)', 'parser.add_argument("--checkpoint-minimum-signals", type=int, default=1000)', "minimum signal default"),
        ('parser.add_argument("--non-overlapping-calendar-days", type=int, default=28)', 'parser.add_argument("--non-overlapping-calendar-days", type=int, default=4)', "non-overlap default"),
        (
            '    args = parser.parse_args()\n\n    random.seed(args.seed)',
            '    args = parser.parse_args()\n\n    if args.horizon_days != 2:\n        raise ValueError("This isolated trainer is fixed to a two-trading-session horizon")\n\n    random.seed(args.seed)',
            "two-day invariant",
        ),
    )
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
    for old, new in (
        ("transformer_20day_sp500_model.pt", "transformer_2day_sp500_model.pt"),
        ("transformer_20day_sp500_scaler.json", "transformer_2day_sp500_scaler.json"),
        ("transformer_20day_sp500_metrics.json", "transformer_2day_sp500_metrics.json"),
        ("transformer_20day_sp500_symbol_summary.json", "transformer_2day_sp500_symbol_summary.json"),
        ("transformer_20day_sp500_config.json", "transformer_2day_sp500_config.json"),
    ):
        text = replace_once(text, old, new, old)
    return text


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    target = build_two_day_source(source)
    compile(target, str(TARGET), "exec")
    TARGET.write_text(target, encoding="utf-8")
    print(f"Created isolated two-day Transformer trainer: {TARGET.name}")


if __name__ == "__main__":
    main()
