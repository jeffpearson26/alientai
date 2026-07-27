from __future__ import annotations

from pathlib import Path

from create_v2_transformer_5day_sp500_trainer import replace_once


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "train_v2_transformer_2day_sp500_from_supabase.py"
TARGET = ROOT / "train_v2_transformer_2day_russell_from_supabase.py"


def build_russell_source(source: str) -> str:
    text = source
    replacements = (
        (
            'BUILD = "ALIENTAI_V2_TRANSFORMER_2DAY_SP500_SUPABASE_TRAINER_V1"',
            'BUILD = "ALIENTAI_V2_TRANSFORMER_2DAY_RUSSELL_SUPABASE_TRAINER_V1"',
            "build identifier",
        ),
        (
            'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_2day_sp500_supabase_training"',
            'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_2day_russell_supabase_training"',
            "output directory",
        ),
        (
            'parser = argparse.ArgumentParser(description="Train isolated V2 two-day daily Transformer model.")',
            'parser = argparse.ArgumentParser(description="Train isolated V2 two-day Russell daily Transformer model.")',
            "parser description",
        ),
    )
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
    for old, new in (
        ("transformer_2day_sp500_model.pt", "transformer_2day_russell_model.pt"),
        ("transformer_2day_sp500_scaler.json", "transformer_2day_russell_scaler.json"),
        ("transformer_2day_sp500_metrics.json", "transformer_2day_russell_metrics.json"),
        ("transformer_2day_sp500_symbol_summary.json", "transformer_2day_russell_symbol_summary.json"),
        ("transformer_2day_sp500_config.json", "transformer_2day_russell_config.json"),
    ):
        text = replace_once(text, old, new, old)
    return text


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    target = build_russell_source(source)
    compile(target, str(TARGET), "exec")
    TARGET.write_text(target, encoding="utf-8")
    print(f"Created isolated two-day Russell Transformer trainer: {TARGET.name}")


if __name__ == "__main__":
    main()
