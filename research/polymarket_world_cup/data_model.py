"""Data model for prediction-market match price series.

A `Match` is a single World Cup game traded as a market with two or more
`Outcome`s (e.g. team-A-wins / draw / team-B-wins, or a binary yes/no).
Each outcome carries a time series of probability prices in [0, 1].

The model is deliberately market-agnostic: Polymarket, Kalshi, or a synthetic
generator all serialize to the same JSON, so the backtest never needs to know
where the data came from.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PricePoint:
    ts: int      # unix seconds
    price: float  # implied probability in [0, 1]


@dataclass
class Outcome:
    outcome_id: str
    name: str
    prices: List[PricePoint] = field(default_factory=list)

    def price_at_or_before(self, ts: int) -> Optional[PricePoint]:
        """Last tick at or before `ts` (the price you could trade at `ts`)."""
        chosen = None
        for p in self.prices:
            if p.ts <= ts:
                chosen = p
            else:
                break
        return chosen

    def ticks_in(self, start_ts: int, end_ts: int) -> List[PricePoint]:
        """In-play ticks on the half-open window [start_ts, end_ts).

        The upper bound is exclusive on purpose: the price exactly at end_ts is
        the *settlement* value (1.0 / 0.0), not a price you could trade in-play.
        Settlement is handled separately by the hold-to-resolution payoff.
        """
        return [p for p in self.prices if start_ts <= p.ts < end_ts]


@dataclass
class Match:
    match_id: str
    description: str
    kickoff_ts: int
    end_ts: int
    # outcome_id of the winner, or None if the match is not yet resolved.
    winning_outcome_id: Optional[str]
    outcomes: List[Outcome] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.winning_outcome_id is not None

    def outcome(self, outcome_id: str) -> Optional[Outcome]:
        for o in self.outcomes:
            if o.outcome_id == outcome_id:
                return o
        return None

    def favorite_at_kickoff(self) -> Optional[Outcome]:
        """Outcome with the highest price at the last pre-kickoff tick.

        Returns None if no outcome has a price at or before kickoff.
        """
        best: Optional[Outcome] = None
        best_price = -1.0
        for o in self.outcomes:
            pp = o.price_at_or_before(self.kickoff_ts)
            if pp is not None and pp.price > best_price:
                best_price = pp.price
                best = o
        return best


# --------------------------------------------------------------------------
# JSON (de)serialization
# --------------------------------------------------------------------------

def match_to_dict(m: Match) -> dict:
    return {
        "match_id": m.match_id,
        "description": m.description,
        "kickoff_ts": m.kickoff_ts,
        "end_ts": m.end_ts,
        "winning_outcome_id": m.winning_outcome_id,
        "outcomes": [
            {
                "outcome_id": o.outcome_id,
                "name": o.name,
                "prices": [{"ts": p.ts, "price": p.price} for p in o.prices],
            }
            for o in m.outcomes
        ],
    }


def match_from_dict(d: dict) -> Match:
    return Match(
        match_id=d["match_id"],
        description=d.get("description", ""),
        kickoff_ts=int(d["kickoff_ts"]),
        end_ts=int(d["end_ts"]),
        winning_outcome_id=d.get("winning_outcome_id"),
        outcomes=[
            Outcome(
                outcome_id=o["outcome_id"],
                name=o.get("name", o["outcome_id"]),
                prices=[PricePoint(int(p["ts"]), float(p["price"])) for p in o.get("prices", [])],
            )
            for o in d.get("outcomes", [])
        ],
    )


def save_matches(matches: List[Match], path: str) -> None:
    with open(path, "w") as f:
        json.dump([match_to_dict(m) for m in matches], f, indent=2)


def load_matches(path: str) -> List[Match]:
    with open(path) as f:
        data = json.load(f)
    return [match_from_dict(d) for d in data]
