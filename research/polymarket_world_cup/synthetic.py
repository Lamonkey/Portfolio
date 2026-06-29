"""Generate a realistic synthetic dataset of World Cup match markets.

This exists so the whole pipeline is runnable and testable without network
access to Polymarket/Kalshi. It is NOT a substitute for real data — the
favorite-longshot edge and the in-play dynamics here are *assumptions* baked
into the generator, so any "result" on synthetic data only reflects those
assumptions. Use it to validate the engine, then run on real data.

Model per match:
  * pick a pre-kickoff favorite probability p0 (binary market: fav vs field).
  * the favorite actually wins with prob p0 + `bias` (small positive `bias`
    => favorite-longshot bias: favorites underpriced).
  * the in-play favorite price follows a Brownian bridge from p0 to the
    settled value (1.0 win / 0.0 loss), with volatility `sigma` producing
    realistic mid-match swings (goals).
"""

from __future__ import annotations

import argparse
import math
import random
from typing import List

from data_model import Match, Outcome, PricePoint, save_matches


def _clip(x: float, lo: float = 0.01, hi: float = 0.99) -> float:
    return max(lo, min(hi, x))


def _brownian_bridge(p0: float, pT: float, n: int, sigma: float, rng: random.Random) -> List[float]:
    """Brownian bridge from p0 to pT over n steps (inclusive), clipped to (0,1)."""
    if n <= 1:
        return [p0, pT][:max(1, n)]
    # standard Brownian motion increments
    w = [0.0]
    for _ in range(n - 1):
        w.append(w[-1] + rng.gauss(0.0, 1.0))
    wT = w[-1]
    path = []
    for i in range(n):
        t = i / (n - 1)
        bridge = w[i] - t * wT          # pinned to 0 at both ends
        val = (1 - t) * p0 + t * pT + sigma * bridge
        path.append(_clip(val))
    path[0] = p0
    return path


def generate(n_matches: int = 64, bias: float = 0.02, sigma: float = 0.18,
             seed: int = 42, match_minutes: int = 100,
             kickoff_base_ts: int = 1_750_000_000) -> List[Match]:
    rng = random.Random(seed)
    matches: List[Match] = []
    for i in range(n_matches):
        # Favorites range from coin-flip-ish to heavy favorites.
        p0 = round(rng.uniform(0.50, 0.85), 3)
        win_prob = _clip(p0 + bias, 0.0, 1.0)
        fav_wins = rng.random() < win_prob

        kickoff = kickoff_base_ts + i * 3 * 86_400          # spread out in time
        # a few pre-kickoff ticks, then 1 tick/min in-play
        pre = [PricePoint(kickoff - 3600 + k * 600, _clip(p0 + rng.gauss(0, 0.01)))
               for k in range(6)]
        pre[-1] = PricePoint(kickoff - 60, p0)              # final pre-kickoff = p0
        end = kickoff + match_minutes * 60

        pT = 0.99 if fav_wins else 0.01
        bridge = _brownian_bridge(p0, pT, match_minutes, sigma, rng)
        inplay = [PricePoint(kickoff + m * 60, bridge[m]) for m in range(match_minutes)]
        # settlement tick exactly at end
        settle = PricePoint(end, 1.0 if fav_wins else 0.0)

        fav_prices = pre + inplay + [settle]
        field_prices = [PricePoint(p.ts, _clip(1.0 - p.price)) for p in fav_prices]

        fav = Outcome("FAV", "Favorite", fav_prices)
        field = Outcome("FIELD", "Field", field_prices)
        matches.append(Match(
            match_id=f"SYN-{i:03d}",
            description=f"Synthetic match {i} (fav p0={p0:.2f})",
            kickoff_ts=kickoff,
            end_ts=end,
            winning_outcome_id="FAV" if fav_wins else "FIELD",
            outcomes=[fav, field],
        ))
    return matches


def main():
    ap = argparse.ArgumentParser(description="Generate synthetic World Cup market data")
    ap.add_argument("--out", default="data/sample_synthetic.json")
    ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--bias", type=float, default=0.02,
                    help="favorite-longshot edge baked in (0 = efficient market)")
    ap.add_argument("--sigma", type=float, default=0.18, help="in-play volatility")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    matches = generate(n_matches=args.n, bias=args.bias, sigma=args.sigma, seed=args.seed)
    save_matches(matches, args.out)
    print(f"wrote {len(matches)} synthetic matches to {args.out} "
          f"(bias={args.bias}, sigma={args.sigma}, seed={args.seed})")


if __name__ == "__main__":
    main()
