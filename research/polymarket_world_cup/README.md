# Polymarket World Cup — Favorite Entry Strategy

A backtest framework for one research question:

> Before a World Cup match, buy the outcome with the **highest implied
> probability** (the favorite). What return do you get under different exit
> strategies — holding to the final whistle vs. selling in-play as the
> probability moves?

It targets **Polymarket** (and is structured to add **Kalshi**) match markets.

## What the research is really measuring

- **Hold-to-resolution** on the favorite is essentially "bet the favorite."
  In an efficient market its expected return is ~0 minus costs. The signal to
  look for is a **favorite–longshot bias**: are favorites slightly *underpriced*
  (they win more often than their price implies)? The report bucket-compares
  implied probability vs. realized win rate to check.
- **Selling in-play** is a bet on the *price path*, not the final outcome. If
  the favorite scores early, the price jumps and you can lock the gain without
  carrying 0-or-1 settlement risk. So the in-play exits trade away variance —
  the comparison shows how much of the value lives in the path vs. the result.

## Layout

| file | role |
|------|------|
| `data_model.py` | `Match` / `Outcome` / `PricePoint` + JSON (de)serialization. Market-agnostic schema. |
| `fetch_polymarket.py` | Pull World Cup markets + price history from Polymarket's public APIs. **Run locally.** |
| `synthetic.py` | Generate a realistic synthetic dataset so the pipeline runs without network. |
| `strategies.py` | Exit strategies: hold-to-resolution, fixed-time, take-profit, stop-loss, OCO, peak-hindsight. |
| `backtest.py` | Entry (buy pre-kickoff favorite) + exit simulation, P&L net of spread/fees. |
| `analyze.py` | Per-strategy stats + favorite–longshot bias table; text report. |
| `run.py` | CLI that ties it together and prints the report (+ optional per-trade CSV). |
| `tests/test_backtest.py` | Engine unit tests on fixtures with known answers. |

## Quick start (no network needed)

```bash
cd research/polymarket_world_cup
python synthetic.py                 # writes data/sample_synthetic.json
python run.py                       # backtest + report
python tests/test_backtest.py       # 10 unit tests
```

## Using real Polymarket data

Outbound access to `*.polymarket.com` is **blocked in the Claude Code web
sandbox**, so fetch on your own machine:

```bash
pip install requests
python fetch_polymarket.py --slug-contains world-cup --closed-only --out data/polymarket_wc.json
python run.py --data data/polymarket_wc.json --csv data/trades.csv
```

Notes on the fetcher:
- Uses the **Gamma API** (`/events`) for the market list + resolution and the
  **CLOB API** (`/prices-history`) for per-outcome price series. No API key.
- `--closed-only` keeps resolved events (required for hold-to-resolution P&L).
- `--fidelity` is the price-bar size in minutes (smaller = finer in-play path).
- Field names (`gameStartTime`, `clobTokenIds`, `outcomePrices`, `closed`) follow
  Polymarket's current Gamma schema; if they drift, adjust `market_to_match`.

## Cost model

`run.py` flags `--spread-bps` (half-spread paid on entry and on any in-play
exit; settlement pays none) and `--fee-bps` (per-trade taker fee). Polymarket
historically charges ~0 trading fee, so `--fee-bps 0` is the default; raise it
to stress-test or to model Kalshi. Returns are **per unit of capital deployed**
so they compare across matches with different entry prices.

## ⚠️ On the synthetic numbers

`synthetic.py` bakes in its own assumptions — a small favorite–longshot `bias`
and an in-play volatility `sigma`. Any "result" on synthetic data only reflects
those knobs; it validates the **engine**, not the **market**. Real conclusions
require real data. Treat the synthetic report as a wiring test.

## Extending to Kalshi

The schema is market-agnostic. Add a `fetch_kalshi.py` that maps Kalshi's
`markets`/`market-candlesticks` endpoints into the same `Match`/`Outcome` JSON,
then `run.py` works unchanged. Kalshi charges trading fees, so set `--fee-bps`.

## Possible next steps

- Stake sizing (Kelly / fixed-fraction) instead of 1 unit/match.
- Per-stage breakdown (group vs. knockout) and home/away effects.
- Sensitivity sweep over take-profit / stop-loss thresholds to find robust ones.
- Bootstrap confidence intervals on mean return (sample sizes are small).
