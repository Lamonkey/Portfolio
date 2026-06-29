"""Fetch World Cup match markets + price history from Polymarket's public APIs.

RUN THIS LOCALLY (or anywhere with outbound access to *.polymarket.com).
It is intentionally dependency-light: only `requests`.

APIs used (both public, no key required):
  * Gamma   https://gamma-api.polymarket.com/events   -> events + their markets
  * CLOB    https://clob.polymarket.com/prices-history -> per-token price series

Each Polymarket market exposes `clobTokenIds` (one CLOB token per outcome) and
`outcomes`. We pull a price series per token, read the resolved winner from
`outcomePrices`, and write everything to the shared JSON schema (data_model).

Usage:
    python fetch_polymarket.py --slug-contains world-cup --out data/polymarket_wc.json
    python fetch_polymarket.py --tag soccer --closed-only --fidelity 1 --out data/wc.json

Then backtest:
    python run.py --data data/polymarket_wc.json
"""

from __future__ import annotations

import argparse
import json
import time
from typing import List, Optional

import requests

from data_model import Match, Outcome, PricePoint, save_matches

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def _get(url: str, params: dict, retries: int = 4) -> dict:
    """GET with exponential backoff on network errors (2/4/8/16s)."""
    delay = 2
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
        except requests.HTTPError as e:
            # 4xx/5xx are not retried blindly; surface them.
            raise
    raise RuntimeError(f"GET {url} failed after retries: {last}")


def fetch_events(slug_contains: Optional[str], tag: Optional[str],
                 closed_only: bool, limit: int) -> List[dict]:
    """Page through Gamma events, optionally filtered by slug substring / tag."""
    events: List[dict] = []
    offset = 0
    page = 100
    while len(events) < limit:
        params = {"limit": page, "offset": offset, "order": "startDate", "ascending": "false"}
        if tag:
            params["tag_slug"] = tag
        if closed_only:
            params["closed"] = "true"
        batch = _get(f"{GAMMA}/events", params)
        if not batch:
            break
        for ev in batch:
            if slug_contains and slug_contains.lower() not in ev.get("slug", "").lower():
                continue
            events.append(ev)
        if len(batch) < page:
            break
        offset += page
    return events[:limit]


def fetch_price_history(token_id: str, fidelity: int = 5) -> List[PricePoint]:
    """Price series for one CLOB token. `fidelity` is the bar size in minutes."""
    data = _get(f"{CLOB}/prices-history", {"market": token_id, "fidelity": fidelity, "interval": "max"})
    return [PricePoint(int(pt["t"]), float(pt["p"])) for pt in data.get("history", [])]


def _parse_list_field(raw) -> list:
    """Gamma returns some list fields as JSON-encoded strings."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    return []


def market_to_match(mkt: dict, fidelity: int) -> Optional[Match]:
    token_ids = _parse_list_field(mkt.get("clobTokenIds"))
    names = _parse_list_field(mkt.get("outcomes"))
    out_prices = _parse_list_field(mkt.get("outcomePrices"))
    if len(token_ids) < 2 or len(names) != len(token_ids):
        return None

    kickoff = mkt.get("gameStartTime") or mkt.get("startDate")
    end = mkt.get("endDate") or mkt.get("closedTime")
    kickoff_ts = _iso_to_ts(kickoff)
    end_ts = _iso_to_ts(end)
    if kickoff_ts is None:
        return None
    if end_ts is None:
        end_ts = kickoff_ts + 3 * 3600  # fallback window

    # Resolved winner: the outcome whose settled price is ~1.
    winner_id = None
    if mkt.get("closed") and out_prices:
        for tid, p in zip(token_ids, out_prices):
            try:
                if float(p) > 0.5:
                    winner_id = tid
                    break
            except (TypeError, ValueError):
                pass

    outcomes: List[Outcome] = []
    for tid, nm in zip(token_ids, names):
        prices = fetch_price_history(tid, fidelity)
        outcomes.append(Outcome(outcome_id=tid, name=str(nm), prices=prices))
        time.sleep(0.1)  # be polite to the API

    return Match(
        match_id=mkt.get("id") or mkt.get("conditionId") or mkt.get("slug", "?"),
        description=mkt.get("question") or mkt.get("groupItemTitle") or mkt.get("slug", ""),
        kickoff_ts=kickoff_ts,
        end_ts=end_ts,
        winning_outcome_id=winner_id,
        outcomes=outcomes,
    )


def _iso_to_ts(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    from datetime import datetime, timezone
    try:
        s = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Fetch World Cup markets from Polymarket")
    ap.add_argument("--slug-contains", default="world-cup",
                    help="keep events whose slug contains this substring")
    ap.add_argument("--tag", default=None, help="Gamma tag_slug filter (e.g. soccer)")
    ap.add_argument("--closed-only", action="store_true",
                    help="only resolved events (needed for hold-to-resolution P&L)")
    ap.add_argument("--limit", type=int, default=50, help="max events to scan")
    ap.add_argument("--fidelity", type=int, default=5, help="price bar size in minutes")
    ap.add_argument("--out", default="data/polymarket_wc.json")
    args = ap.parse_args()

    events = fetch_events(args.slug_contains, args.tag, args.closed_only, args.limit)
    print(f"found {len(events)} matching events")

    matches: List[Match] = []
    for ev in events:
        for mkt in ev.get("markets", []):
            try:
                m = market_to_match(mkt, args.fidelity)
            except Exception as e:  # one bad market shouldn't kill the run
                print(f"  skip market {mkt.get('id')}: {e}")
                continue
            if m and any(o.prices for o in m.outcomes):
                matches.append(m)
                print(f"  + {m.description[:60]}  ({len(m.outcomes)} outcomes, "
                      f"{'resolved' if m.resolved else 'open'})")

    save_matches(matches, args.out)
    print(f"\nwrote {len(matches)} matches to {args.out}")


if __name__ == "__main__":
    main()
