from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import torch
from torch import nn

from alientai_v2.engines.base_engine import make_candidate
from alientai_v2.utils import safe_float


ENGINE_ID = "transformer_20day"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

MODEL_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day"
MODEL_PATH = MODEL_DIR / "transformer_20day_model.pt"
SCALER_PATH = MODEL_DIR / "transformer_20day_scaler.json"
CONFIG_PATH = MODEL_DIR / "transformer_20day_config.json"

MASTER_POLICY_PATH = (
    PROJECT_ROOT
    / "data_v2"
    / "prediction_20day_daily_training"
    / "prediction_20day_master_symbol_policy.json"
)

DEFAULT_TABLE = "v2_daily_candles"

_MODEL_CACHE = None
_CONFIG_CACHE = None
_SCALER_CACHE = None
_POLICY_CACHE = None


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
            os.environ.setdefault(key, value)


def env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


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
    clean = [safe_float(v, 0.0) for v in values if v is not None]
    if not clean:
        return default
    return sum(clean) / len(clean)


def stdev(values: List[float], default: float = 0.0) -> float:
    clean = [safe_float(v, 0.0) for v in values if v is not None]
    if len(clean) < 2:
        return default

    m = mean(clean)
    var = sum((v - m) ** 2 for v in clean) / (len(clean) - 1)
    return math.sqrt(var)


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
        last = encoded[:, -1, :]
        logits = self.head(last).squeeze(-1)
        return logits


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default
    return default


def load_config() -> Dict[str, Any]:
    global _CONFIG_CACHE

    if isinstance(_CONFIG_CACHE, dict):
        return _CONFIG_CACHE

    config = load_json(CONFIG_PATH, {})

    if not isinstance(config, dict):
        config = {}

    _CONFIG_CACHE = config
    return config


def load_scaler() -> Dict[str, Any]:
    global _SCALER_CACHE

    if isinstance(_SCALER_CACHE, dict):
        return _SCALER_CACHE

    scaler = load_json(SCALER_PATH, {})

    if not isinstance(scaler, dict):
        scaler = {}

    _SCALER_CACHE = scaler
    return scaler


def load_master_policy() -> Dict[str, Dict[str, Any]]:
    global _POLICY_CACHE

    if isinstance(_POLICY_CACHE, dict):
        return _POLICY_CACHE

    raw = load_json(MASTER_POLICY_PATH, {})

    policy_map = {}

    if isinstance(raw, dict) and isinstance(raw.get("policy"), dict):
        policy_map = raw.get("policy", {})
    elif isinstance(raw, dict):
        policy_map = raw

    normalized: Dict[str, Dict[str, Any]] = {}

    if isinstance(policy_map, dict):
        for symbol, value in policy_map.items():
            sym = str(symbol or "").upper().strip()
            if not sym:
                continue

            if isinstance(value, dict):
                info = dict(value)
                info["policy"] = str(info.get("policy") or "NO_DATA").upper()
                normalized[sym] = info
            else:
                normalized[sym] = {
                    "policy": str(value or "NO_DATA").upper()
                }

    _POLICY_CACHE = normalized
    return normalized


def get_master_policy(symbol: str) -> Dict[str, Any]:
    symbol = str(symbol or "").upper().strip()
    return load_master_policy().get(symbol, {"policy": "NO_DATA"})


def load_model() -> Tuple[Optional[TimeSeriesTransformer], Dict[str, Any], Dict[str, Any], str]:
    global _MODEL_CACHE

    config = load_config()
    scaler = load_scaler()

    if _MODEL_CACHE is not None:
        return _MODEL_CACHE, config, scaler, ""

    if not MODEL_PATH.exists():
        return None, config, scaler, f"Missing transformer model file: {MODEL_PATH}"

    if not scaler:
        return None, config, scaler, f"Missing transformer scaler file: {SCALER_PATH}"

    input_size = safe_int(config.get("input_size"), 16)
    sequence_length = safe_int(config.get("sequence_length"), 60)
    d_model = safe_int(config.get("d_model"), 64)
    heads = safe_int(config.get("heads"), 4)
    layers = safe_int(config.get("layers"), 2)
    dropout = safe_float(config.get("dropout"), 0.10)

    try:
        model = TimeSeriesTransformer(
            input_size=input_size,
            sequence_length=sequence_length,
            d_model=d_model,
            nhead=heads,
            num_layers=layers,
            dim_feedforward=d_model * 2,
            dropout=dropout,
        )

        state = torch.load(MODEL_PATH, map_location="cpu")
        model.load_state_dict(state)
        model.eval()

        _MODEL_CACHE = model
        return model, config, scaler, ""

    except Exception as exc:
        return None, config, scaler, f"Transformer model load failed: {exc}"


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
    timeout: int = 45,
) -> List[Dict[str, Any]]:
    url = supabase_url.rstrip("/") + f"/rest/v1/{table}"

    response = requests.get(
        url,
        headers=supabase_headers(supabase_key),
        params=params,
        timeout=timeout,
    )

    if response.status_code not in {200, 206}:
        raise RuntimeError(f"Supabase HTTP {response.status_code}: {response.text[:500]}")

    value = response.json()

    if isinstance(value, list):
        return value

    return []


def fetch_daily_candles(symbol: str, limit: int = 280, table: str = DEFAULT_TABLE) -> List[Dict[str, Any]]:
    load_env_file(ENV_PATH)

    supabase_url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        return []

    symbol = str(symbol or "").upper().strip()

    params = {
        "select": "symbol,timeframe,datetime_ms,datetime_utc,date,open,high,low,close,volume",
        "symbol": f"eq.{symbol}",
        "timeframe": "eq.1d",
        "order": "datetime_ms.desc",
        "limit": str(limit),
    }

    rows = supabase_get(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        table=table,
        params=params,
    )

    candles: List[Dict[str, Any]] = []
    seen = set()

    for raw in rows:
        if not isinstance(raw, dict):
            continue

        datetime_ms = safe_int(raw.get("datetime_ms"), 0)

        if datetime_ms <= 0 or datetime_ms in seen:
            continue

        seen.add(datetime_ms)

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


def build_bar_features(candles: List[Dict[str, Any]]) -> List[List[float]]:
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

    return rows


def build_latest_sequence(candles: List[Dict[str, Any]], sequence_length: int) -> Optional[torch.Tensor]:
    if len(candles) < max(sequence_length, 220):
        return None

    features = build_bar_features(candles)
    seq = features[-sequence_length:]

    if len(seq) != sequence_length:
        return None

    return torch.tensor([seq], dtype=torch.float32)


def apply_scaler(x: torch.Tensor, scaler: Dict[str, Any]) -> torch.Tensor:
    mean_values = scaler.get("mean", [])
    std_values = scaler.get("std", [])

    if not isinstance(mean_values, list) or not isinstance(std_values, list):
        return x

    if not mean_values or not std_values:
        return x

    mean_tensor = torch.tensor(mean_values, dtype=torch.float32).view(1, 1, -1)
    std_tensor = torch.tensor(std_values, dtype=torch.float32).view(1, 1, -1)
    std_tensor = torch.where(std_tensor.abs() < 1e-6, torch.ones_like(std_tensor), std_tensor)

    return (x - mean_tensor) / std_tensor


def score_to_decision(
    symbol: str,
    probability: float,
    policy_info: Dict[str, Any],
    settings: Dict[str, Any],
) -> Tuple[str, float, str]:
    policy = str(policy_info.get("policy", "NO_DATA")).upper()

    min_watch = safe_float(settings.get("transformer_20day_min_watch_probability"), 0.60)
    min_buy = safe_float(settings.get("transformer_20day_min_buy_probability"), 0.70)

    score = round(probability * 100.0, 2)

    allow_buy_policies = {"ALLOW_BUY_STRONG", "ALLOW_BUY", "ALLOW_SMALL"}

    reason = (
        f"Transformer 20-day probability {probability:.3f}. "
        f"Master20dPolicy={policy}. "
        f"Master buy win={policy_info.get('buy_candidate_win_rate_pct')}. "
        f"Master avg buy return={policy_info.get('avg_buy_future_20d_return_pct')}."
    )

    if policy in {"BLOCK_BUY", "NO_DATA"}:
        return "AVOID", min(score, 39.0), reason + " Policy blocks transformer buy."

    if policy == "WATCH_ONLY":
        if probability >= min_watch:
            return "WATCH", min(score, 49.0), reason + " Watch-only policy."
        return "AVOID", min(score, 39.0), reason + " Watch-only but probability too low."

    if policy in allow_buy_policies:
        if probability >= min_buy:
            return "BUY_CANDIDATE", score, reason + " Transformer buy threshold passed."

        if probability >= min_watch:
            return "WATCH", score, reason + " Transformer watch threshold passed."

        return "AVOID", score, reason + " Transformer probability below watch threshold."

    return "AVOID", min(score, 39.0), reason + " Unknown policy blocks buy."


def scan(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    model, config, scaler, load_error = load_model()

    if load_error or model is None:
        candidates.append({
            "engine_id": ENGINE_ID,
            "symbol": "",
            "decision": "AVOID",
            "score": 0.0,
            "price": 0.0,
            "source": ENGINE_ID,
            "reason": load_error or "Transformer model unavailable.",
        })
        return candidates

    sequence_length = safe_int(config.get("sequence_length"), 60)
    table = str(settings.get("transformer_20day_daily_table", DEFAULT_TABLE))
    candle_limit = safe_int(settings.get("transformer_20day_candle_limit"), 280)
    max_symbols = safe_int(settings.get("transformer_20day_max_symbols_per_scan"), 40)
    delay = safe_float(settings.get("transformer_20day_symbol_delay_seconds"), 0.02)

    symbols_seen = 0

    for quote in quotes:
        symbol = str(quote.get("symbol") or quote.get("ticker") or "").upper().strip()

        if not symbol:
            continue

        symbols_seen += 1

        if max_symbols > 0 and symbols_seen > max_symbols:
            break

        price = safe_float(quote.get("price"), 0.0)
        policy_info = get_master_policy(symbol)

        try:
            candles = fetch_daily_candles(symbol, limit=candle_limit, table=table)

            if len(candles) < max(sequence_length, 220):
                candidates.append({
                    "engine_id": ENGINE_ID,
                    "symbol": symbol,
                    "decision": "AVOID",
                    "score": 0.0,
                    "price": price,
                    "source": ENGINE_ID,
                    "reason": f"Not enough daily candles for transformer: {len(candles)}.",
                    "transformer_20day_probability": None,
                    "prediction_horizon_days": 20,
                    "master_policy": policy_info.get("policy"),
                })
                continue

            x = build_latest_sequence(candles, sequence_length=sequence_length)

            if x is None:
                continue

            x = apply_scaler(x, scaler)

            with torch.no_grad():
                logits = model(x)
                probability = float(torch.sigmoid(logits)[0].item())

            decision, score, reason = score_to_decision(
                symbol=symbol,
                probability=probability,
                policy_info=policy_info,
                settings=settings,
            )

            candidates.append(
                make_candidate(
                    engine_id=ENGINE_ID,
                    symbol=symbol,
                    side="LONG",
                    score=score,
                    decision=decision,
                    price=price,
                    prediction_horizon_minutes=20 * 24 * 60,
                    minimum_hold_minutes=20 * 24 * 60,
                    reason=reason,
                    quote=quote,
                    warnings=[],
                    reasons=[
                        f"Transformer probability: {probability:.3f}",
                        f"Master policy: {policy_info.get('policy')}",
                        f"Master buy win rate: {policy_info.get('buy_candidate_win_rate_pct')}",
                        f"Master avg buy return: {policy_info.get('avg_buy_future_20d_return_pct')}",
                    ],
                )
            )

            candidates[-1]["transformer_20day_probability"] = round(probability, 6)
            candidates[-1]["transformer_20day_model_path"] = str(MODEL_PATH)
            candidates[-1]["transformer_20day_policy"] = policy_info.get("policy")
            candidates[-1]["transformer_20day_master_buy_win_rate_pct"] = policy_info.get("buy_candidate_win_rate_pct")
            candidates[-1]["transformer_20day_master_avg_buy_return_pct"] = policy_info.get("avg_buy_future_20d_return_pct")
            candidates[-1]["transformer_20day_daily_candles"] = len(candles)

        except Exception as exc:
            candidates.append({
                "engine_id": ENGINE_ID,
                "symbol": symbol,
                "decision": "AVOID",
                "score": 0.0,
                "price": price,
                "source": ENGINE_ID,
                "reason": f"Transformer engine error for {symbol}: {exc}",
                "transformer_20day_probability": None,
                "prediction_horizon_days": 20,
                "master_policy": policy_info.get("policy"),
            })

        if delay > 0:
            time.sleep(delay)

    candidates.sort(key=lambda row: safe_float(row.get("score"), 0.0), reverse=True)
    return candidates
