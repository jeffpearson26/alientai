from __future__ import annotations

"""Train the frozen autonomous AlienTAI 20-session champion candidate."""

import train_nasdaq101_126session_technical_model as trainer


trainer.HORIZON_SESSIONS = 20
trainer.EMBARGO_SESSIONS = 20
trainer.HAC_LAG_SESSIONS = 19
trainer.PORTFOLIO_SLOTS = trainer.MAX_DAILY_SELECTIONS * 20
trainer.TARGET = "label_20d_net_return_pct"
trainer.GROSS = "label_20d_gross_return_pct"
trainer.LABEL_END = "label_20d_exit_market_date"
trainer.MODEL_TARGET = "model_excess_to_qqq_20d_pct"
trainer.MIN_DECISION_PRICE = 5.0
trainer.MIN_AVERAGE_DOLLAR_VOLUME_20D = 20_000_000.0
trainer.MIN_NONOVERLAP_OBSERVED_FOLDS = 4
trainer.MIN_NONOVERLAP_POSITIVE_FOLDS = 3
trainer.POLICY_PERCENTILES = (90.0, 95.0, 97.5, 99.0)


if __name__ == "__main__":
    trainer.main()
