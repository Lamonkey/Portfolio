"""Backtest engine: buy the pre-kickoff favorite, exit per a strategy.

Costs modelled (parameterized; both default to small but non-zero):
  * spread_bps  -- half-spread paid on entry (buy above mid) and on any
                   in-play exit (sell below mid). Settlement pays no spread.
  * fee_bps     -- per-trade taker fee on notional, charged on entry and on
                   any in-play exit (not on settlement).

Returns are per 1 unit of capital deployed in the trade, i.e.
    return_pct = (net_proceeds - net_cost) / net_cost
so they are directly comparable across matches with different entry prices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from data_model import Match
from strategies import Strategy


@dataclass
class Trade:
    match_id: str
    description: str
    strategy: str
    favorite: str
    entry_price: float     # mid price at entry
    net_cost: float        # what we actually paid per share (entry + spread + fee)
    exit_price: float      # gross proceeds per share (mid / settlement)
    net_proceeds: float    # what we actually received per share
    resolved: bool         # held to settlement vs sold in-play
    won: bool              # did the favorite ultimately win
    return_pct: float
    note: str


def backtest_match(match: Match, strategy: Strategy,
                   spread_bps: float = 50.0, fee_bps: float = 0.0) -> Optional[Trade]:
    """Run one match through one strategy. Returns None if the match can't be
    traded (no pre-kickoff price, or unresolved when the strategy needs it)."""
    fav = match.favorite_at_kickoff()
    if fav is None:
        return None
    entry_pp = fav.price_at_or_before(match.kickoff_ts)
    entry_mid = entry_pp.price
    if entry_mid <= 0.0 or entry_mid >= 1.0:
        return None  # degenerate / already-settled price

    res = strategy.exit(match, fav, entry_mid, match.kickoff_ts)
    if res.resolved and not match.resolved:
        return None  # strategy needs settlement but match isn't resolved

    spread = spread_bps / 10_000.0
    fee = fee_bps / 10_000.0

    # Entry: pay above mid by half-spread, plus taker fee on notional.
    net_cost = entry_mid * (1.0 + spread) + entry_mid * fee

    if res.resolved:
        # Settlement: receive 1.0 or 0.0, no spread, no fee.
        net_proceeds = res.gross_proceeds
    else:
        # In-play sale: receive below mid by half-spread, minus taker fee.
        net_proceeds = res.gross_proceeds * (1.0 - spread) - res.gross_proceeds * fee

    return Trade(
        match_id=match.match_id,
        description=match.description,
        strategy=strategy.name,
        favorite=fav.name,
        entry_price=entry_mid,
        net_cost=net_cost,
        exit_price=res.gross_proceeds,
        net_proceeds=net_proceeds,
        resolved=res.resolved,
        won=(match.winning_outcome_id == fav.outcome_id),
        return_pct=(net_proceeds - net_cost) / net_cost,
        note=res.note,
    )


def backtest(matches: List[Match], strategy: Strategy,
             spread_bps: float = 50.0, fee_bps: float = 0.0) -> List[Trade]:
    out = []
    for m in matches:
        t = backtest_match(m, strategy, spread_bps, fee_bps)
        if t is not None:
            out.append(t)
    return out
