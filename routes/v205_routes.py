from typing import Any

from research_brain.paper_trade_engine import (
    account_summary,
    build_paper_orders,
    execute_paper_orders,
    reset_paper_account,
    set_paper_settings,
)


def install_v205_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v205/status")
    def alpha_v205_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V205_PAPER_TRADE_ENGINE",
            "message": "Paper trade abilities are installed.",
            "routes": [
                "/alpha/paper/account",
                "/alpha/paper/preview-morning-buys",
                "/alpha/paper/execute-morning-buys",
                "/alpha/paper/reset",
                "/alpha/paper/settings",
            ],
            "safety_note": "This is paper-only. It does not send live brokerage orders.",
        }

    @app.get("/alpha/paper/account")
    def alpha_paper_account():
        return account_summary()

    @app.get("/alpha/paper/preview-morning-buys")
    def alpha_paper_preview_morning_buys(
        max_positions: int | None = None,
        max_dollars_per_position: float | None = None,
        min_confidence: float | None = None,
        min_rank_score: float | None = None,
        allow_buying_indexes: bool | None = None,
    ):
        return build_paper_orders(
            max_positions=max_positions,
            max_dollars_per_position=max_dollars_per_position,
            min_confidence=min_confidence,
            min_rank_score=min_rank_score,
            allow_buying_indexes=allow_buying_indexes,
        )

    @app.post("/alpha/paper/execute-morning-buys")
    def alpha_paper_execute_morning_buys(
        max_positions: int | None = None,
        max_dollars_per_position: float | None = None,
        min_confidence: float | None = None,
        min_rank_score: float | None = None,
        allow_buying_indexes: bool | None = None,
    ):
        return execute_paper_orders(
            max_positions=max_positions,
            max_dollars_per_position=max_dollars_per_position,
            min_confidence=min_confidence,
            min_rank_score=min_rank_score,
            allow_buying_indexes=allow_buying_indexes,
        )

    @app.post("/alpha/paper/reset")
    def alpha_paper_reset(starting_cash: float = 10000.0):
        return reset_paper_account(starting_cash=starting_cash)

    @app.post("/alpha/paper/settings")
    def alpha_paper_settings(
        paper_trading_enabled: bool | None = None,
        max_new_positions_per_run: int | None = None,
        max_dollars_per_position: float | None = None,
        min_confidence: float | None = None,
        min_rank_score: float | None = None,
        allow_buying_indexes: bool | None = None,
        preserve_cash: float | None = None,
    ):
        return set_paper_settings(
            paper_trading_enabled=paper_trading_enabled,
            max_new_positions_per_run=max_new_positions_per_run,
            max_dollars_per_position=max_dollars_per_position,
            min_confidence=min_confidence,
            min_rank_score=min_rank_score,
            allow_buying_indexes=allow_buying_indexes,
            preserve_cash=preserve_cash,
        )

    return app
