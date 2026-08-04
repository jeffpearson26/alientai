import unittest

from alientai_v2.research.exact_multileg_option_compiler import (
    OptionLeg,
    compile_exact_trade,
)


def snapshot(available, bid, ask, include=True):
    return {
        "available_at_utc": available,
        "contracts": (
            [{"contractID": "C1", "bid": bid, "ask": ask}] if include else
            [{"contractID": "OTHER", "bid": bid, "ask": ask}]
        ),
    }


class ExactMultilegCompilerTests(unittest.TestCase):
    def test_long_leg_crosses_ask_then_bid_and_charges_fees(self):
        result = compile_exact_trade(
            legs=[OptionLeg("C1", "long")],
            selection_snapshot=snapshot("2026-01-01T21:10:00+00:00", 1.0, 1.2),
            selected_at_utc="2026-01-01T21:11:00+00:00",
            entry_snapshot=snapshot("2026-01-02T21:10:00+00:00", 1.4, 1.5),
            exit_snapshot=snapshot("2026-01-09T21:10:00+00:00", 1.9, 2.0),
            maximum_risk_dollars=150,
        )
        self.assertEqual(result["gross_pnl_dollars"], 40.0)
        self.assertEqual(result["net_pnl_dollars"], 38.7)

    def test_same_snapshot_selection_and_entry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timing"):
            compile_exact_trade(
                legs=[OptionLeg("C1", "long")],
                selection_snapshot=snapshot("2026-01-02T21:10:00+00:00", 1, 2),
                selected_at_utc="2026-01-02T21:11:00+00:00",
                entry_snapshot=snapshot("2026-01-02T21:10:00+00:00", 1, 2),
                exit_snapshot=snapshot("2026-01-09T21:10:00+00:00", 2, 3),
                maximum_risk_dollars=200,
            )

    def test_missing_exact_contract_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            compile_exact_trade(
                legs=[OptionLeg("C1", "long")],
                selection_snapshot=snapshot("2026-01-01T21:10:00+00:00", 1, 2),
                selected_at_utc="2026-01-01T21:11:00+00:00",
                entry_snapshot=snapshot("2026-01-02T21:10:00+00:00", 1, 2),
                exit_snapshot=snapshot("2026-01-09T21:10:00+00:00", 2, 3, False),
                maximum_risk_dollars=200,
            )


if __name__ == "__main__":
    unittest.main()
