"""Aggregate backtest results: per-strategy stats + favorite-longshot bias."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

from backtest import Trade


@dataclass
class StrategyStats:
    strategy: str
    n: int
    win_rate: float          # share of trades where the favorite won (resolution view)
    mean_return: float       # mean per-trade return_pct
    median_return: float
    std_return: float
    total_pnl_per_unit: float  # sum of return_pct if you staked 1 unit per match
    sharpe: float            # mean / std (per-trade, not annualized)
    pct_held_to_resolution: float


def _median(xs: List[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _std(xs: List[float], mean: float) -> float:
    if len(xs) < 2:
        return 0.0
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def summarize(trades: List[Trade]) -> StrategyStats:
    rets = [t.return_pct for t in trades]
    n = len(trades)
    mean = sum(rets) / n if n else 0.0
    std = _std(rets, mean)
    return StrategyStats(
        strategy=trades[0].strategy if trades else "(none)",
        n=n,
        win_rate=sum(1 for t in trades if t.won) / n if n else 0.0,
        mean_return=mean,
        median_return=_median(rets),
        std_return=std,
        total_pnl_per_unit=sum(rets),
        sharpe=(mean / std) if std > 0 else 0.0,
        pct_held_to_resolution=sum(1 for t in trades if t.resolved) / n if n else 0.0,
    )


@dataclass
class BiasBucket:
    lo: float
    hi: float
    n: int
    avg_entry_price: float   # = avg implied probability
    realized_win_rate: float
    edge: float              # realized - implied (positive => favorites underpriced)


def favorite_longshot_bias(trades: List[Trade], n_buckets: int = 5) -> List[BiasBucket]:
    """Compare implied probability (entry price) to realized win rate, bucketed
    by entry price. Uses hold-to-resolution semantics, so pass trades from the
    HoldToResolution strategy (or any strategy — `won` is outcome-based)."""
    edges = [0.5 + 0.5 * i / n_buckets for i in range(n_buckets + 1)]  # favorites: 0.5..1.0
    buckets: List[BiasBucket] = []
    for i in range(n_buckets):
        lo, hi = edges[i], edges[i + 1]
        in_b = [t for t in trades if lo <= t.entry_price < hi or (i == n_buckets - 1 and t.entry_price == hi)]
        if not in_b:
            continue
        avg_p = sum(t.entry_price for t in in_b) / len(in_b)
        wr = sum(1 for t in in_b if t.won) / len(in_b)
        buckets.append(BiasBucket(lo, hi, len(in_b), avg_p, wr, wr - avg_p))
    return buckets


def format_report(results: Dict[str, List[Trade]],
                  spread_bps: float, fee_bps: float,
                  resolution_key: str = "hold_to_resolution") -> str:
    lines: List[str] = []
    lines.append("=" * 78)
    lines.append("POLYMARKET WORLD CUP — FAVORITE ENTRY STRATEGY BACKTEST")
    lines.append("=" * 78)
    lines.append(f"costs: spread={spread_bps:g}bps (half each side), fee={fee_bps:g}bps per trade")
    lines.append("returns are per unit of capital deployed; +0.10 = +10%")
    lines.append("")

    header = f"{'strategy':<24}{'n':>4}{'win%':>7}{'mean':>9}{'median':>9}{'std':>8}{'sharpe':>8}{'held%':>7}"
    lines.append(header)
    lines.append("-" * len(header))
    for name, trades in results.items():
        if not trades:
            lines.append(f"{name:<24}{0:>4}  (no tradeable matches)")
            continue
        s = summarize(trades)
        lines.append(
            f"{s.strategy:<24}{s.n:>4}{s.win_rate * 100:>6.1f}%"
            f"{s.mean_return * 100:>8.2f}%{s.median_return * 100:>8.2f}%"
            f"{s.std_return * 100:>7.1f}%{s.sharpe:>8.2f}{s.pct_held_to_resolution * 100:>6.0f}%"
        )
    lines.append("")

    # Favorite-longshot bias from the hold-to-resolution trades.
    base = results.get(resolution_key) or next((t for t in results.values() if t), [])
    if base:
        lines.append("FAVORITE–LONGSHOT BIAS (implied vs realized, hold-to-resolution)")
        lines.append(f"{'price bucket':<16}{'n':>5}{'implied':>10}{'realized':>10}{'edge':>9}")
        lines.append("-" * 50)
        for b in favorite_longshot_bias(base):
            lines.append(
                f"{f'[{b.lo:.2f},{b.hi:.2f})':<16}{b.n:>5}"
                f"{b.avg_entry_price * 100:>9.1f}%{b.realized_win_rate * 100:>9.1f}%"
                f"{b.edge * 100:>+8.1f}%"
            )
        lines.append("")
        lines.append("edge > 0  => favorites win MORE often than priced (underpriced; bet them)")
        lines.append("edge < 0  => favorites win LESS often than priced (overpriced)")
    lines.append("")
    return "\n".join(lines)
