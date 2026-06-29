"""CLI: run the favorite-entry backtest over a dataset and print the report.

    python run.py --data data/sample_synthetic.json
    python run.py --data data/sample_synthetic.json --spread-bps 50 --fee-bps 0 --csv out.csv

If --data is omitted and the sample file is missing, a synthetic dataset is
generated on the fly so you can see output immediately.
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List

from analyze import format_report
from backtest import Trade, backtest
from data_model import load_matches
from strategies import default_strategies


def write_csv(results: Dict[str, List[Trade]], path: str) -> None:
    fields = ["strategy", "match_id", "description", "favorite", "entry_price",
              "net_cost", "exit_price", "net_proceeds", "resolved", "won",
              "return_pct", "note"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for trades in results.values():
            for t in trades:
                w.writerow({k: getattr(t, k) for k in fields})


def main():
    ap = argparse.ArgumentParser(description="Backtest 'buy the favorite before kickoff'")
    ap.add_argument("--data", default="data/sample_synthetic.json")
    ap.add_argument("--spread-bps", type=float, default=50.0)
    ap.add_argument("--fee-bps", type=float, default=0.0)
    ap.add_argument("--csv", default=None, help="optional path to dump per-trade rows")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        print(f"[info] {args.data} not found; generating synthetic data")
        from synthetic import generate
        from data_model import save_matches
        os.makedirs(os.path.dirname(args.data) or ".", exist_ok=True)
        save_matches(generate(), args.data)

    matches = load_matches(args.data)
    print(f"loaded {len(matches)} matches from {args.data} "
          f"({sum(1 for m in matches if m.resolved)} resolved)\n")

    results: Dict[str, List[Trade]] = {}
    for strat in default_strategies():
        results[strat.name] = backtest(matches, strat, args.spread_bps, args.fee_bps)

    print(format_report(results, args.spread_bps, args.fee_bps))

    if args.csv:
        write_csv(results, args.csv)
        print(f"per-trade rows written to {args.csv}")


if __name__ == "__main__":
    main()
