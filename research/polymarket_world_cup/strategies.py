"""Exit strategies for the "buy the favorite before kickoff" trade.

Every strategy answers one question: given that we bought the favorite at
`entry_price` just before kickoff, how and when do we get out?

Each returns an `ExitResult`:
  * resolved=True  -> we held to settlement; gross_proceeds is 1.0 (favorite
                      won) or 0.0 (favorite lost). No exit spread is paid.
  * resolved=False -> we sold in-play at `exit_ts` for `gross_proceeds`
                      (a probability price in [0, 1]); the backtester applies
                      the sell-side spread + fee on top.

`gross_proceeds` is per 1 share and is always pre-fee / pre-exit-spread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from data_model import Match, Outcome, PricePoint


@dataclass
class ExitResult:
    exit_ts: int
    gross_proceeds: float   # per share, in [0, 1]
    resolved: bool          # True if held to settlement
    note: str = ""


class Strategy:
    name = "base"

    def exit(self, match: Match, fav: Outcome, entry_price: float, entry_ts: int) -> ExitResult:
        raise NotImplementedError

    def _won(self, match: Match, fav: Outcome) -> bool:
        return match.winning_outcome_id == fav.outcome_id

    def _resolution(self, match: Match, fav: Outcome, note: str = "held to resolution") -> ExitResult:
        return ExitResult(match.end_ts, 1.0 if self._won(match, fav) else 0.0, True, note)


class HoldToResolution(Strategy):
    name = "hold_to_resolution"

    def exit(self, match, fav, entry_price, entry_ts):
        return self._resolution(match, fav)


class FixedTime(Strategy):
    """Sell at the first tick at least `offset_seconds` after kickoff
    (e.g. offset=45*60 ~ halftime). Falls back to resolution if the match
    has no in-play tick that late."""

    def __init__(self, offset_seconds: int, label: Optional[str] = None):
        self.offset = offset_seconds
        self.name = label or f"fixed_time_{offset_seconds // 60}min"

    def exit(self, match, fav, entry_price, entry_ts):
        target_ts = match.kickoff_ts + self.offset
        for p in fav.prices:
            if target_ts <= p.ts < match.end_ts:
                return ExitResult(p.ts, p.price, False, f"sold at +{self.offset // 60}min")
        return self._resolution(match, fav, "no tick at offset; held to resolution")


class TakeProfit(Strategy):
    """Sell the first time the favorite's in-play price rises to a target.

    Set EITHER `delta` (target = entry_price + delta) OR `target` (absolute).
    If the target is never hit in-play, hold to resolution.
    """

    def __init__(self, delta: Optional[float] = None, target: Optional[float] = None,
                 label: Optional[str] = None):
        if (delta is None) == (target is None):
            raise ValueError("specify exactly one of delta or target")
        self.delta = delta
        self.target = target
        if label:
            self.name = label
        elif delta is not None:
            self.name = f"take_profit_+{delta:g}"
        else:
            self.name = f"take_profit_at_{target:g}"

    def exit(self, match, fav, entry_price, entry_ts):
        tgt = self.target if self.target is not None else entry_price + self.delta
        for p in fav.ticks_in(match.kickoff_ts, match.end_ts):
            if p.price >= tgt:
                # Fill at the target (a resting limit order would fill there);
                # if the tick gapped above, you'd realistically get the tick.
                fill = min(p.price, tgt) if p.price >= tgt else p.price
                return ExitResult(p.ts, fill, False, f"hit target {tgt:.3f}")
        return self._resolution(match, fav, f"target {tgt:.3f} never hit; held to resolution")


class StopLoss(Strategy):
    """Sell the first time the favorite's in-play price falls by `delta`
    (or to absolute `floor`). Otherwise hold to resolution."""

    def __init__(self, delta: Optional[float] = None, floor: Optional[float] = None,
                 label: Optional[str] = None):
        if (delta is None) == (floor is None):
            raise ValueError("specify exactly one of delta or floor")
        self.delta = delta
        self.floor = floor
        if label:
            self.name = label
        elif delta is not None:
            self.name = f"stop_loss_-{delta:g}"
        else:
            self.name = f"stop_loss_at_{floor:g}"

    def exit(self, match, fav, entry_price, entry_ts):
        flr = self.floor if self.floor is not None else entry_price - self.delta
        for p in fav.ticks_in(match.kickoff_ts, match.end_ts):
            if p.price <= flr:
                fill = max(p.price, flr) if p.price <= flr else p.price
                return ExitResult(p.ts, fill, False, f"hit stop {flr:.3f}")
        return self._resolution(match, fav, f"stop {flr:.3f} never hit; held to resolution")


class TakeProfitStopLoss(Strategy):
    """One-cancels-other: whichever of take-profit / stop-loss triggers first
    in time wins; otherwise hold to resolution. The realistic 'sell in-play'
    strategy."""

    def __init__(self, tp_delta: float, sl_delta: float, label: Optional[str] = None):
        self.tp_delta = tp_delta
        self.sl_delta = sl_delta
        self.name = label or f"oco_+{tp_delta:g}_-{sl_delta:g}"

    def exit(self, match, fav, entry_price, entry_ts):
        tp = entry_price + self.tp_delta
        sl = entry_price - self.sl_delta
        for p in fav.ticks_in(match.kickoff_ts, match.end_ts):
            if p.price >= tp:
                return ExitResult(p.ts, min(p.price, tp), False, f"take-profit {tp:.3f}")
            if p.price <= sl:
                return ExitResult(p.ts, max(p.price, sl), False, f"stop-loss {sl:.3f}")
        return self._resolution(match, fav, "neither trigger hit; held to resolution")


class PeakHindsight(Strategy):
    """Sell at the in-play maximum price. NOT tradeable (it peeks at the
    future) — it's an upper bound on what any in-play exit could achieve."""

    name = "peak_hindsight"

    def exit(self, match, fav, entry_price, entry_ts):
        ticks = fav.ticks_in(match.kickoff_ts, match.end_ts)
        if not ticks:
            return self._resolution(match, fav, "no in-play ticks")
        best = max(ticks, key=lambda p: p.price)
        return ExitResult(best.ts, best.price, False, "sold at in-play peak")


def default_strategies() -> List[Strategy]:
    """The standard comparison set used by run.py."""
    return [
        HoldToResolution(),
        FixedTime(45 * 60, label="sell_at_halftime"),
        FixedTime(75 * 60, label="sell_at_75min"),
        TakeProfit(delta=0.15, label="take_profit_+0.15"),
        StopLoss(delta=0.15, label="stop_loss_-0.15"),
        TakeProfitStopLoss(tp_delta=0.15, sl_delta=0.15, label="oco_+/-0.15"),
        PeakHindsight(),
    ]
