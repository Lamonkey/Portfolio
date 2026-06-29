"""Unit tests for the backtest engine on hand-built fixtures with known answers.

Run from the project root:
    python -m pytest research/polymarket_world_cup/tests -q
or without pytest:
    python research/polymarket_world_cup/tests/test_backtest.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backtest import backtest_match  # noqa: E402
from data_model import Match, Outcome, PricePoint  # noqa: E402
from strategies import (  # noqa: E402
    FixedTime, HoldToResolution, PeakHindsight, StopLoss, TakeProfit,
)

K = 1_000_000          # kickoff ts
END = K + 100 * 60     # 100-minute match


def make_match(fav_path, won, field_start=0.4):
    """fav_path: list of (minute_offset, price) in-play. Adds a pre-kickoff
    tick at K-60 equal to the first in-play price, and a settlement tick."""
    p0 = fav_path[0][1]
    fav_prices = [PricePoint(K - 60, p0)]
    fav_prices += [PricePoint(K + m * 60, pr) for m, pr in fav_path]
    fav_prices.append(PricePoint(END, 1.0 if won else 0.0))
    field_prices = [PricePoint(p.ts, round(1 - p.price, 4)) for p in fav_prices]
    return Match(
        match_id="T", description="test", kickoff_ts=K, end_ts=END,
        winning_outcome_id="FAV" if won else "FIELD",
        outcomes=[Outcome("FAV", "Favorite", fav_prices),
                  Outcome("FIELD", "Field", field_prices)],
    )


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_favorite_selection_picks_highest_prekickoff():
    m = make_match([(0, 0.65), (50, 0.7)], won=True)
    t = backtest_match(m, HoldToResolution(), spread_bps=0, fee_bps=0)
    assert t.favorite == "Favorite"
    assert approx(t.entry_price, 0.65)


def test_hold_to_resolution_win_zero_cost():
    m = make_match([(0, 0.60)], won=True)
    t = backtest_match(m, HoldToResolution(), spread_bps=0, fee_bps=0)
    # bought at 0.60, settles at 1.0 -> return = (1-0.6)/0.6
    assert approx(t.return_pct, (1.0 - 0.6) / 0.6)
    assert t.resolved and t.won


def test_hold_to_resolution_loss():
    m = make_match([(0, 0.60)], won=False)
    t = backtest_match(m, HoldToResolution(), spread_bps=0, fee_bps=0)
    assert approx(t.return_pct, -1.0)  # total loss
    assert not t.won


def test_fixed_time_sells_at_offset():
    # price rises to 0.8 by minute 45
    path = [(0, 0.6), (45, 0.8), (90, 0.5)]
    m = make_match(path, won=False)  # outcome irrelevant; we exit in-play
    t = backtest_match(m, FixedTime(45 * 60), spread_bps=0, fee_bps=0)
    assert not t.resolved
    assert approx(t.exit_price, 0.8)
    assert approx(t.return_pct, (0.8 - 0.6) / 0.6)


def test_take_profit_triggers_and_caps_at_target():
    path = [(0, 0.6), (30, 0.78)]  # +0.15 target = 0.75, tick gaps to 0.78
    m = make_match(path, won=True)
    t = backtest_match(m, TakeProfit(delta=0.15), spread_bps=0, fee_bps=0)
    assert not t.resolved
    assert approx(t.exit_price, 0.75)  # filled at target, not 0.78


def test_take_profit_never_hit_holds_to_resolution():
    path = [(0, 0.6), (30, 0.62)]
    m = make_match(path, won=True)
    t = backtest_match(m, TakeProfit(delta=0.15), spread_bps=0, fee_bps=0)
    assert t.resolved and approx(t.return_pct, (1.0 - 0.6) / 0.6)


def test_stop_loss_triggers():
    path = [(0, 0.6), (20, 0.40)]  # -0.15 stop = 0.45
    m = make_match(path, won=False)
    t = backtest_match(m, StopLoss(delta=0.15), spread_bps=0, fee_bps=0)
    assert not t.resolved
    assert approx(t.exit_price, 0.45)
    assert approx(t.return_pct, (0.45 - 0.6) / 0.6)


def test_peak_hindsight_takes_max():
    path = [(0, 0.6), (10, 0.7), (20, 0.95), (30, 0.5)]
    m = make_match(path, won=False)
    t = backtest_match(m, PeakHindsight(), spread_bps=0, fee_bps=0)
    assert approx(t.exit_price, 0.95)


def test_spread_and_fee_reduce_return():
    m = make_match([(0, 0.6)], won=True)
    no_cost = backtest_match(m, HoldToResolution(), spread_bps=0, fee_bps=0)
    with_cost = backtest_match(m, HoldToResolution(), spread_bps=100, fee_bps=50)
    # settlement pays no spread/fee, but entry cost is higher -> lower return
    assert with_cost.return_pct < no_cost.return_pct


def test_unresolved_match_skipped_for_resolution_strategy():
    m = make_match([(0, 0.6)], won=True)
    m.winning_outcome_id = None  # mark unresolved
    assert backtest_match(m, HoldToResolution()) is None


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
