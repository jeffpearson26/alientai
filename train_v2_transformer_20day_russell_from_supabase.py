from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


BUILD = "ALIENTAI_V2_TRANSFORMER_20DAY_RUSSELL_SUPABASE_TRAINER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day_russell_supabase_training"

DEFAULT_TABLE = "v2_daily_candles"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and value:
            os.environ[key] = value


def env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def pct_change(old: float, new: float) -> float:
    old = safe_float(old, 0.0)
    new = safe_float(new, 0.0)

    if old <= 0:
        return 0.0

    return ((new - old) / old) * 100.0


def mean(values: List[float], default: float = 0.0) -> float:
    values = [safe_float(v, 0.0) for v in values if v is not None]
    if not values:
        return default
    return sum(values) / len(values)


def stdev(values: List[float], default: float = 0.0) -> float:
    values = [safe_float(v, 0.0) for v in values if v is not None]
    if len(values) < 2:
        return default
    m = mean(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def read_symbols_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Symbols file not found: {path}")

    symbols: List[str] = []

    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        symbol = line.strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        symbols.append(symbol)

    return sorted(set(symbols))


def supabase_headers(key: str) -> Dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def supabase_get(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    params: Dict[str, str],
    timeout: int = 90,
) -> List[Dict[str, Any]]:
    url = supabase_url.rstrip("/") + f"/rest/v1/{table}"

    response = requests.get(
        url,
        headers=supabase_headers(supabase_key),
        params=params,
        timeout=timeout,
    )

    if response.status_code not in {200, 206}:
        raise RuntimeError(f"Supabase HTTP {response.status_code}: {response.text[:1000]}")

    return response.json()


def fetch_daily_candles(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    symbol: str,
    limit: int,
) -> List[Dict[str, Any]]:
    symbol = str(symbol or "").upper().strip()

    all_rows: List[Dict[str, Any]] = []
    page_size = 1000
    before_ms: Optional[int] = None

    while len(all_rows) < limit:
        remaining = limit - len(all_rows)
        this_limit = min(page_size, remaining)

        params = {
            "select": "symbol,timeframe,datetime_ms,datetime_utc,date,open,high,low,close,volume",
            "symbol": f"eq.{symbol}",
            "timeframe": "eq.1d",
            "order": "datetime_ms.desc",
            "limit": str(this_limit),
        }

        if before_ms is not None:
            params["datetime_ms"] = f"lt.{before_ms}"

        rows = supabase_get(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table=table,
            params=params,
        )

        if not rows:
            break

        all_rows.extend(rows)

        page_min_ms = min(safe_int(r.get("datetime_ms"), 0) for r in rows)

        if page_min_ms <= 0:
            break

        before_ms = page_min_ms

        if len(rows) < this_limit:
            break

        time.sleep(0.02)

    candles: List[Dict[str, Any]] = []
    seen = set()

    for raw in all_rows:
        datetime_ms = safe_int(raw.get("datetime_ms"), 0)

        if datetime_ms <= 0:
            continue

        key = (symbol, datetime_ms)
        if key in seen:
            continue
        seen.add(key)

        candles.append({
            "symbol": symbol,
            "datetime_ms": datetime_ms,
            "datetime_utc": str(raw.get("datetime_utc") or ""),
            "date": str(raw.get("date") or ""),
            "open": safe_float(raw.get("open"), 0.0),
            "high": safe_float(raw.get("high"), 0.0),
            "low": safe_float(raw.get("low"), 0.0),
            "close": safe_float(raw.get("close"), 0.0),
            "volume": safe_float(raw.get("volume"), 0.0),
        })

    candles.sort(key=lambda r: int(r.get("datetime_ms") or 0))
    return candles


def rolling_mean(values: List[float], end_idx: int, days: int) -> float:
    start = end_idx - days + 1
    if start < 0:
        return 0.0
    return mean(values[start:end_idx + 1], 0.0)


def rolling_high(values: List[float], end_idx: int, days: int) -> float:
    start = end_idx - days + 1
    if start < 0:
        return 0.0
    return max(values[start:end_idx + 1])


def rolling_low(values: List[float], end_idx: int, days: int) -> float:
    start = end_idx - days + 1
    if start < 0:
        return 0.0
    return min(values[start:end_idx + 1])


def build_bar_features(candles: List[Dict[str, Any]]) -> np.ndarray:
    """
    Converts daily candles into per-day features.

    Each day becomes a small numeric feature vector.
    Later, sequence windows are cut from this matrix.
    """
    closes = [safe_float(c.get("close"), 0.0) for c in candles]
    highs = [safe_float(c.get("high"), 0.0) for c in candles]
    lows = [safe_float(c.get("low"), 0.0) for c in candles]
    opens = [safe_float(c.get("open"), 0.0) for c in candles]
    volumes = [safe_float(c.get("volume"), 0.0) for c in candles]

    rows: List[List[float]] = []

    for i in range(len(candles)):
        close = closes[i]
        open_ = opens[i]
        high = highs[i]
        low = lows[i]
        volume = volumes[i]

        if close <= 0:
            rows.append([0.0] * 16)
            continue

        prev_close = closes[i - 1] if i > 0 else close

        day_return = pct_change(prev_close, close)
        open_to_close = pct_change(open_, close) if open_ > 0 else 0.0
        high_low_range = ((high - low) / close) * 100.0 if close > 0 else 0.0

        ret_5 = pct_change(closes[i - 5], close) if i >= 5 else 0.0
        ret_10 = pct_change(closes[i - 10], close) if i >= 10 else 0.0
        ret_20 = pct_change(closes[i - 20], close) if i >= 20 else 0.0
        ret_50 = pct_change(closes[i - 50], close) if i >= 50 else 0.0

        sma20 = rolling_mean(closes, i, 20)
        sma50 = rolling_mean(closes, i, 50)
        sma200 = rolling_mean(closes, i, 200)

        close_vs_sma20 = pct_change(sma20, close) if sma20 > 0 else 0.0
        close_vs_sma50 = pct_change(sma50, close) if sma50 > 0 else 0.0
        close_vs_sma200 = pct_change(sma200, close) if sma200 > 0 else 0.0

        high20 = rolling_high(highs, i, 20)
        low20 = rolling_low(lows, i, 20)

        drawdown20 = pct_change(high20, close) if high20 > 0 else 0.0

        position_in_20_range = 0.5
        if high20 > low20:
            position_in_20_range = (close - low20) / (high20 - low20)

        vol20_values: List[float] = []
        for j in range(max(1, i - 19), i + 1):
            vol20_values.append(pct_change(closes[j - 1], closes[j]))

        volatility20 = stdev(vol20_values, 0.0)

        vol_sma20 = rolling_mean(volumes, i, 20)
        vol_sma50 = rolling_mean(volumes, i, 50)

        volume_ratio_20_50 = vol_sma20 / vol_sma50 if vol_sma50 > 0 else 1.0
        volume_today_vs_20 = volume / vol_sma20 if vol_sma20 > 0 else 1.0

        rows.append([
            day_return,
            open_to_close,
            high_low_range,
            ret_5,
            ret_10,
            ret_20,
            ret_50,
            close_vs_sma20,
            close_vs_sma50,
            close_vs_sma200,
            drawdown20,
            position_in_20_range,
            volatility20,
            volume_ratio_20_50,
            volume_today_vs_20,
            1.0 if close > sma200 and sma200 > 0 else 0.0,
        ])

    return np.array(rows, dtype=np.float32)


def make_symbol_windows(
    *,
    symbol: str,
    candles: List[Dict[str, Any]],
    sequence_length: int,
    horizon_days: int,
    min_history_days: int,
    step_days: int,
) -> Tuple[List[np.ndarray], List[int], List[float], List[Dict[str, Any]]]:
    if len(candles) < min_history_days + horizon_days + 1:
        return [], [], [], []

    features = build_bar_features(candles)
    closes = [safe_float(c.get("close"), 0.0) for c in candles]

    x_list: List[np.ndarray] = []
    y_list: List[int] = []
    return_list: List[float] = []
    meta_list: List[Dict[str, Any]] = []

    start_idx = max(min_history_days, sequence_length)
    end_idx = len(candles) - horizon_days - 1

    for idx in range(start_idx, end_idx, step_days):
        start = idx - sequence_length + 1
        end = idx + 1

        seq = features[start:end]

        if seq.shape[0] != sequence_length:
            continue

        now_close = closes[idx]
        future_close = closes[idx + horizon_days]

        if now_close <= 0 or future_close <= 0:
            continue

        future_return = pct_change(now_close, future_close)
        label = 1 if future_return > 0 else 0

        x_list.append(seq)
        y_list.append(label)
        return_list.append(future_return)
        meta_list.append({
            "symbol": symbol,
            "date": candles[idx].get("date"),
            "datetime_ms": candles[idx].get("datetime_ms"),
            "close": now_close,
            "future_return_pct": future_return,
        })

    return x_list, y_list, return_list, meta_list


class TimeSeriesTransformer(nn.Module):
    def __init__(
        self,
        input_size: int,
        sequence_length: int,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.10,
    ):
        super().__init__()

        self.sequence_length = sequence_length
        self.input_projection = nn.Linear(input_size, d_model)
        self.position_embedding = nn.Parameter(torch.zeros(1, sequence_length, d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )

        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_projection(x)
        x = x + self.position_embedding
        encoded = self.encoder(x)

        # Use the last time step as the sequence summary.
        last = encoded[:, -1, :]
        logits = self.head(last).squeeze(-1)
        return logits


def standardize_train_val(
    x_train: np.ndarray,
    x_val: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    mean_ = x_train.mean(axis=(0, 1), keepdims=True)
    std_ = x_train.std(axis=(0, 1), keepdims=True)

    std_[std_ < 1e-6] = 1.0

    x_train_scaled = (x_train - mean_) / std_
    x_val_scaled = (x_val - mean_) / std_

    scaler = {
        "mean": mean_.reshape(-1).tolist(),
        "std": std_.reshape(-1).tolist(),
    }

    return x_train_scaled.astype(np.float32), x_val_scaled.astype(np.float32), scaler


def binary_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    preds = (probabilities >= threshold).astype(np.int64)

    total = len(y_true)
    correct = int((preds == y_true).sum())

    positives = int((preds == 1).sum())
    actual_positives = int((y_true == 1).sum())

    true_positive = int(((preds == 1) & (y_true == 1)).sum())
    false_positive = int(((preds == 1) & (y_true == 0)).sum())
    false_negative = int(((preds == 0) & (y_true == 1)).sum())

    accuracy = correct / total if total else 0.0
    precision = true_positive / positives if positives else 0.0
    recall = true_positive / actual_positives if actual_positives else 0.0

    return {
        "threshold": threshold,
        "total": total,
        "accuracy": round(accuracy, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "predicted_positive_count": positives,
        "actual_positive_count": actual_positives,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def evaluate_model(
    model: nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    future_returns: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> Dict[str, Any]:
    model.eval()

    probabilities: List[float] = []

    loader = DataLoader(
        TensorDataset(torch.tensor(x, dtype=torch.float32)),
        batch_size=batch_size,
        shuffle=False,
    )

    with torch.no_grad():
        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            logits = model(batch_x)
            probs = torch.sigmoid(logits).detach().cpu().numpy()
            probabilities.extend(probs.tolist())

    probabilities_np = np.array(probabilities, dtype=np.float32)

    metrics = {
        "base_up_rate": round(float(y.mean()), 6) if len(y) else 0.0,
        "avg_future_return_pct": round(float(future_returns.mean()), 6) if len(future_returns) else 0.0,
        "thresholds": [],
    }

    for threshold in [0.50, 0.55, 0.60, 0.65, 0.70]:
        threshold_metrics = binary_metrics(y, probabilities_np, threshold=threshold)

        selected_returns = future_returns[probabilities_np >= threshold]
        if len(selected_returns):
            threshold_metrics["avg_selected_future_return_pct"] = round(float(selected_returns.mean()), 6)
            threshold_metrics["selected_win_rate"] = round(float((selected_returns > 0).mean()), 6)
        else:
            threshold_metrics["avg_selected_future_return_pct"] = None
            threshold_metrics["selected_win_rate"] = None

        metrics["thresholds"].append(threshold_metrics)

    return metrics


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train V2 20-day daily transformer model.")
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--symbols-file", required=True)
    parser.add_argument("--limit-symbols", type=int, default=0)
    parser.add_argument("--candle-limit", type=int, default=10000)
    parser.add_argument("--sequence-length", type=int, default=60)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--min-history-days", type=int, default=260)
    parser.add_argument("--step-days", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    load_env_file(ENV_PATH)

    supabase_url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing from .env.")

    if not supabase_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    symbols = read_symbols_file(Path(args.symbols_file))

    if args.limit_symbols and args.limit_symbols > 0:
        symbols = symbols[:args.limit_symbols]

    print(f"Build: {BUILD}")
    print(f"Symbols: {len(symbols)}")
    print(f"Table: {args.table}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Sequence length: {args.sequence_length}")
    print(f"Horizon days: {args.horizon_days}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print("This does NOT touch the V2 paper account.")
    print("")

    all_x: List[np.ndarray] = []
    all_y: List[int] = []
    all_returns: List[float] = []
    all_meta: List[Dict[str, Any]] = []

    symbol_summaries: List[Dict[str, Any]] = []

    for index, symbol in enumerate(symbols, start=1):
        print(f"[{index}/{len(symbols)}] Fetching/building windows {symbol}...")

        try:
            candles = fetch_daily_candles(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table=args.table,
                symbol=symbol,
                limit=args.candle_limit,
            )

            x_list, y_list, return_list, meta_list = make_symbol_windows(
                symbol=symbol,
                candles=candles,
                sequence_length=args.sequence_length,
                horizon_days=args.horizon_days,
                min_history_days=args.min_history_days,
                step_days=args.step_days,
            )

            all_x.extend(x_list)
            all_y.extend(y_list)
            all_returns.extend(return_list)
            all_meta.extend(meta_list)

            symbol_summaries.append({
                "symbol": symbol,
                "status": "success",
                "candles": len(candles),
                "windows": len(x_list),
                "up_rate": round(float(np.mean(y_list)), 6) if y_list else None,
                "avg_future_return_pct": round(float(np.mean(return_list)), 6) if return_list else None,
            })

            print(f"  candles={len(candles)} windows={len(x_list)}")

        except Exception as exc:
            symbol_summaries.append({
                "symbol": symbol,
                "status": "error",
                "candles": 0,
                "windows": 0,
                "error": str(exc),
            })
            print(f"  ERROR {symbol}: {exc}")

        if args.delay > 0:
            time.sleep(args.delay)

    if not all_x:
        raise RuntimeError("No training windows were created.")

    x = np.stack(all_x).astype(np.float32)
    y = np.array(all_y, dtype=np.int64)
    future_returns = np.array(all_returns, dtype=np.float32)

    # Time-aware split using metadata datetime order.
    order = np.argsort(np.array([safe_int(m.get("datetime_ms"), 0) for m in all_meta], dtype=np.int64))

    x = x[order]
    y = y[order]
    future_returns = future_returns[order]
    all_meta = [all_meta[int(i)] for i in order]

    split_index = int(len(x) * 0.80)

    x_train = x[:split_index]
    y_train = y[:split_index]
    returns_train = future_returns[:split_index]

    x_val = x[split_index:]
    y_val = y[split_index:]
    returns_val = future_returns[split_index:]

    x_train, x_val, scaler = standardize_train_val(x_train, x_val)

    train_loader = DataLoader(
        TensorDataset(
            torch.tensor(x_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        ),
        batch_size=args.batch_size,
        shuffle=True,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = TimeSeriesTransformer(
        input_size=x_train.shape[2],
        sequence_length=args.sequence_length,
        d_model=args.d_model,
        nhead=args.heads,
        num_layers=args.layers,
        dim_feedforward=args.d_model * 2,
        dropout=args.dropout,
    ).to(device)

    positive_rate = float(y_train.mean()) if len(y_train) else 0.5
    positive_rate = min(max(positive_rate, 0.01), 0.99)
    pos_weight_value = (1.0 - positive_rate) / positive_rate

    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor([pos_weight_value], dtype=torch.float32).to(device)
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.001)

    train_history: List[Dict[str, Any]] = []

    print("")
    print("Training...")

    for epoch in range(1, args.epochs + 1):
        model.train()
        losses: List[float] = []

        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

            optimizer.step()
            losses.append(float(loss.detach().cpu().item()))

        train_loss = float(np.mean(losses)) if losses else 0.0

        val_metrics = evaluate_model(
            model=model,
            x=x_val,
            y=y_val,
            future_returns=returns_val,
            batch_size=args.batch_size,
            device=device,
        )

        epoch_row = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_base_up_rate": val_metrics.get("base_up_rate"),
            "val_threshold_055": next(
                (m for m in val_metrics["thresholds"] if m["threshold"] == 0.55),
                {},
            ),
            "val_threshold_060": next(
                (m for m in val_metrics["thresholds"] if m["threshold"] == 0.60),
                {},
            ),
        }

        train_history.append(epoch_row)

        print(
            f"  epoch {epoch}/{args.epochs} "
            f"loss={train_loss:.6f} "
            f"base_up={val_metrics.get('base_up_rate')} "
            f"t55_win={epoch_row['val_threshold_055'].get('selected_win_rate')} "
            f"t60_win={epoch_row['val_threshold_060'].get('selected_win_rate')}"
        )

    final_train_metrics = evaluate_model(
        model=model,
        x=x_train,
        y=y_train,
        future_returns=returns_train,
        batch_size=args.batch_size,
        device=device,
    )

    final_val_metrics = evaluate_model(
        model=model,
        x=x_val,
        y=y_val,
        future_returns=returns_val,
        batch_size=args.batch_size,
        device=device,
    )

    model_path = OUT_DIR / "transformer_20day_russell_model.pt"
    scaler_path = OUT_DIR / "transformer_20day_russell_scaler.json"
    metrics_path = OUT_DIR / "transformer_20day_russell_metrics.json"
    symbol_summary_path = OUT_DIR / "transformer_20day_russell_symbol_summary.json"
    config_path = OUT_DIR / "transformer_20day_russell_config.json"

    torch.save(model.state_dict(), model_path)

    write_json(scaler_path, scaler)
    write_json(symbol_summary_path, symbol_summaries)

    config = {
        "build": BUILD,
        "created_at": now_iso(),
        "input_size": int(x_train.shape[2]),
        "sequence_length": args.sequence_length,
        "horizon_days": args.horizon_days,
        "min_history_days": args.min_history_days,
        "step_days": args.step_days,
        "d_model": args.d_model,
        "heads": args.heads,
        "layers": args.layers,
        "dropout": args.dropout,
        "symbols_file": args.symbols_file,
        "symbols_used": symbols,
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
    }

    write_json(config_path, config)

    metrics = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "device": str(device),
        "torch_version": torch.__version__,
        "symbols_seen": len(symbols),
        "total_windows": int(len(x)),
        "train_windows": int(len(x_train)),
        "validation_windows": int(len(x_val)),
        "train_base_up_rate": round(float(y_train.mean()), 6),
        "validation_base_up_rate": round(float(y_val.mean()), 6),
        "train_avg_future_return_pct": round(float(returns_train.mean()), 6),
        "validation_avg_future_return_pct": round(float(returns_val.mean()), 6),
        "train_metrics": final_train_metrics,
        "validation_metrics": final_val_metrics,
        "train_history": train_history,
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "config_path": str(config_path),
        "symbol_summary_path": str(symbol_summary_path),
    }

    write_json(metrics_path, metrics)

    print("")
    print("DONE")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
