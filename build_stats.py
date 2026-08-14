"""Compute the homepage statistics from the cleaned Grad Café dataset.

Reads the Module 8 cleaning output (96,948 rows) and writes the small
aggregate file the website renders — so every number on the homepage is
reproducible from the data rather than typed by hand.

    python build_stats.py ../module_8/cleaned_gradcafe.json

Writes flask_website/data/site_stats.json.
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "flask_website" / "data" / "site_stats.json"

# Only plot GPA buckets with enough observations to be meaningful.
MIN_BUCKET = 150
DECIDED = ("Accepted", "Rejected")


def build(path: str) -> dict:
    """Aggregate the cleaned dataset into the figures the site displays."""
    with open(path, encoding="utf-8") as source_file:
        rows = json.load(source_file)

    outcomes = collections.Counter(r.get("outcome") for r in rows)
    accepted = outcomes.get("Accepted", 0)
    rejected = outcomes.get("Rejected", 0)

    # Acceptance rate per 0.1 GPA bucket, decided outcomes only.
    buckets: dict[float, list[int]] = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        gpa, outcome = row.get("GPA"), row.get("outcome")
        if gpa is None or outcome not in DECIDED:
            continue
        try:
            gpa = float(gpa)
        except (TypeError, ValueError):
            continue
        if not 2.0 <= gpa <= 4.0:
            continue
        bucket = round(gpa * 10) / 10
        buckets[bucket][0] += 1
        if outcome == "Accepted":
            buckets[bucket][1] += 1

    curve = [
        {"gpa": k, "n": v[0], "rate": round(100 * v[1] / v[0], 1)}
        for k, v in sorted(buckets.items())
        if v[0] >= MIN_BUCKET
    ]

    gpas = []
    for row in rows:
        try:
            value = float(row.get("GPA"))
        except (TypeError, ValueError):
            continue
        # Same plausible band the curve uses, so the median describes the
        # population the figure plots rather than a wider one.
        if 2.0 <= value <= 4.0:
            gpas.append(value)

    decided = accepted + rejected
    if not decided or not gpas:
        raise SystemExit(
            f"{path}: no decided outcomes ({decided}) or no usable GPAs "
            f"({len(gpas)}) — check the input file."
        )

    return {
        "generated_from": Path(path).name,
        "records": len(rows),
        "universities": len({r.get("University") for r in rows if r.get("University")}),
        "programs": len({r.get("Program") for r in rows if r.get("Program")}),
        "acceptance_rate": round(100 * accepted / decided, 1),
        "median_gpa": round(statistics.median(gpas), 2),
        "gpa_curve": curve,
    }


if __name__ == "__main__":
    default = Path(__file__).resolve().parent.parent / "module_8" / "cleaned_gradcafe.json"
    source = sys.argv[1] if len(sys.argv) > 1 else str(default)
    stats = build(source)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    print(f"wrote {OUT} — {stats['records']:,} records, "
          f"{len(stats['gpa_curve'])} GPA buckets")
