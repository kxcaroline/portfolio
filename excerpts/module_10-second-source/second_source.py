"""Second-source comparison: FDA approvals vs ClinicalTrials.gov trials.

Joins the two sources on the SAME six therapy classes to answer a question
neither answers alone: which crowded classes are *converting* trials into
approved products, and which are still purely developmental.

    trials      (fetch_data.py  -> visualization.build_population)  "starting"
    approvals   (fetch_fda.py   -> fda_approvals.csv)               "arriving"

Produces a per-class summary (trials, approvals, approvals per 1,000 trials,
first-approval year), a paired trials-vs-approvals figure, and a cumulative
approval timeline.

Run (after both fetches):
    python second_source.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import visualization as viz

MODULE_DIR = Path(__file__).resolve().parent
APPROVALS_CSV = MODULE_DIR / "fda_approvals.csv"


def load_approvals(path: Path = APPROVALS_CSV) -> pd.DataFrame:
    """Load fda_approvals.csv produced by fetch_fda.py.

    Args:
        path: Location of the approvals CSV.

    Returns:
        One row per approved agent, with a ``classes`` string column.

    Raises:
        SystemExit: If the file is missing, with regeneration guidance.
    """
    if not path.exists():
        raise SystemExit(
            f"Approvals dataset not found: {path}\n"
            "Run `python fetch_fda.py` first to create it (see README)."
        )
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def summarize(pop: pd.DataFrame, approvals: pd.DataFrame) -> pd.DataFrame:
    """Per-class trials, approvals (all-time and in-decade), and conversion.

    The conversion rate is deliberately window-consistent: it divides approvals
    that fall inside the trial decade (``START_YEAR``-``END_YEAR``) by the
    decade's trials, so the two counts cover the same period. ``approvals`` (all
    time) is kept for the arrival-history view; ``first_approval_year`` can
    predate the decade (cytokines were approved in the 1980s-90s).

    Args:
        pop: The six-class trial analysis population.
        approvals: The FDA approvals frame from :func:`load_approvals`.

    Returns:
        DataFrame indexed by class with ``trials``, ``approvals``,
        ``approvals_in_decade``, ``approvals_per_1000_trials`` and
        ``first_approval_year``.
    """
    flags = viz.approval_class_flags(approvals)
    rows = []
    for name in viz.CLASS_ORDER:
        trials = int(pop[name].sum())
        years = pd.to_numeric(approvals.loc[flags[name], "approval_year"],
                              errors="coerce").dropna()
        in_decade = int(years.between(viz.START_YEAR, viz.END_YEAR).sum())
        rows.append({
            "class": name,
            "trials": trials,
            "approvals": int(len(years)),
            "approvals_in_decade": in_decade,
            "approvals_per_1000_trials": round(in_decade / trials * 1000, 2)
            if trials else float("nan"),
            "first_approval_year": int(years.min()) if not years.empty else None,
        })
    return pd.DataFrame(rows).set_index("class")


def main() -> None:
    """Build the comparison summary and write both figures."""
    pop = viz.build_population(viz.load_trials())
    approvals = load_approvals()
    summary = summarize(pop, approvals)
    print(summary.to_string())
    viz.plot_trials_vs_approvals(summary)
    viz.plot_approval_timeline(approvals)
    print(f"\nWrote {viz.TRIALS_VS_APPROVALS_PNG.name} and "
          f"{viz.APPROVAL_TIMELINE_PNG.name}")


if __name__ == "__main__":
    main()
