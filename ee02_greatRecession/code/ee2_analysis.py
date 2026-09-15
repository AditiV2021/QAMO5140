"""Empirical Exercise 2: Great Recession data-vintage comparison."""

import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
MPL_CONFIG = OUTPUT / ".matplotlib"
MPL_CONFIG.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG))

import matplotlib.pyplot as plt


START, END = "2007-01-01", "2013-12-01"
BASE = pd.Timestamp("2007-01-01")


def input_path(name: str) -> Path:
    """Use the specified CSV, while accepting the supplied Excel-wrapped CSV files."""
    csv = DATA / name
    if csv.exists():
        return csv
    xlsx = DATA / f"{name}.xlsx"
    if xlsx.exists():
        return xlsx
    if name == "gdpc1_today.csv" and (DATA / "GDPC1.csv").exists():
        return DATA / "GDPC1.csv"
    raise FileNotFoundError(f"Missing input file: {csv}")


def load_series(name: str, quarterly: bool) -> pd.Series:
    path = input_path(name)
    frame = pd.read_excel(path) if path.suffix == ".xlsx" else pd.read_csv(path)
    date_col = "DATE" if "DATE" in frame.columns else "observation_date"
    value_cols = [c for c in frame.columns if c != date_col]
    if len(value_cols) != 1:
        raise ValueError(f"{path.name} must have exactly one value column")
    series = pd.Series(
        pd.to_numeric(frame[value_cols[0]], errors="raise").to_numpy(),
        index=pd.to_datetime(frame[date_col]),
        name=name.removesuffix(".csv"),
    ).sort_index()
    if quarterly:
        series = series.resample("QS").mean()
    return series.loc[START:END]


def quarters_since_base(index: pd.DatetimeIndex) -> np.ndarray:
    return ((index.year - BASE.year) * 4 + (index.quarter - 1)).to_numpy()


def shade_recession(ax: plt.Axes) -> None:
    ax.axvspan(3, 9, color="0.85", zorder=0)  # 2007:Q4 through 2009:Q2


def main() -> None:
    gdp_2009 = load_series("gdpc1_vintage_2009q1.csv", quarterly=True)
    gdp_2010 = load_series("gdpc1_vintage_2010q1.csv", quarterly=True)
    gdp_today = load_series("gdpc1_today.csv", quarterly=True)
    potential_2008 = load_series("gdppot_vintage_2008.csv", quarterly=True)
    potential_today = load_series("gdppot_today.csv", quarterly=True)
    core_pce = load_series("pcepilfe.csv", quarterly=True)
    fed_funds = load_series("fedfunds.csv", quarterly=True)

    index = pd.date_range(START, END, freq="QS")
    data = pd.DataFrame(index=index)
    data.index.name = "date"
    data["gdpc1_2009q1_vintage"] = gdp_2009.reindex(index)
    data["gdpc1_2010q1_vintage"] = gdp_2010.reindex(index)
    data["gdpc1_today"] = gdp_today.reindex(index)
    data["gdppot_2008_vintage"] = potential_2008.reindex(index)
    data["gdppot_today"] = potential_today.reindex(index)
    data["core_pce"] = core_pce.reindex(index)
    data["fedfunds"] = fed_funds.reindex(index)

    for column in ["gdpc1_2009q1_vintage", "gdpc1_2010q1_vintage", "gdpc1_today"]:
        data[f"{column}_cumulative_pct_change"] = 100 * (data[column] / data.loc[BASE, column] - 1)

    growth_2009 = 400 * np.log(data.loc["2008-10-01", "gdpc1_2009q1_vintage"] / data.loc["2008-07-01", "gdpc1_2009q1_vintage"])
    growth_today = 400 * np.log(data.loc["2008-10-01", "gdpc1_today"] / data.loc["2008-07-01", "gdpc1_today"])
    print(f"2008:Q4 annualized growth, 2009:Q1 vintage: {growth_2009:.2f}%")
    print(f"2008:Q4 annualized growth, today: {growth_today:.2f}%")
    if abs(growth_2009 - (-3.8)) > 1.0 or abs(growth_today - (-8.5)) > 1.0:
        raise RuntimeError("GDP-growth sanity check failed: expected approximately -3.8 and -8.5.")
    print("GDP-growth sanity check: PASS")

    zero_columns = [c for c in data if c.endswith("_cumulative_pct_change")]
    if not np.allclose(data.loc[BASE, zero_columns].to_numpy(dtype=float), 0.0, atol=1e-12):
        raise RuntimeError("GDP-index sanity check failed: not all GDP indices equal zero at 2007:Q1.")
    print("GDP-index sanity check (all three equal 0 at 2007:Q1): PASS")

    x = quarters_since_base(data.index)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for column, label in [
        ("gdpc1_2009q1_vintage_cumulative_pct_change", "2009:Q1 vintage"),
        ("gdpc1_2010q1_vintage_cumulative_pct_change", "2010:Q1 vintage"),
        ("gdpc1_today_cumulative_pct_change", "Today"),
    ]:
        ax.plot(x, data[column], linewidth=2, label=label)
    shade_recession(ax)
    ax.set(xlabel="Quarters since January 2007", ylabel="Cumulative percent change in real GDP")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUT / "chart1_gdp_vintages.png", dpi=150)
    plt.close(fig)

    data["core_pce_yoy_inflation"] = 100 * (data["core_pce"] / data["core_pce"].shift(4) - 1)
    data["output_gap_realtime"] = 100 * np.log(data["gdpc1_2009q1_vintage"] / data["gdppot_2008_vintage"])
    base_gap = data.loc[BASE, "output_gap_realtime"]
    data["output_gap_today"] = base_gap + 100 * np.log(
        (data["gdpc1_today"] / data.loc[BASE, "gdpc1_today"])
        / (data["gdppot_2008_vintage"] / data.loc[BASE, "gdppot_2008_vintage"])
    )
    data["bernanke_rule_realtime"] = data["core_pce_yoy_inflation"] + data["output_gap_realtime"] + 0.5 * (data["core_pce_yoy_inflation"] - 2) + 2
    data["bernanke_rule_today"] = data["core_pce_yoy_inflation"] + data["output_gap_today"] + 0.5 * (data["core_pce_yoy_inflation"] - 2) + 2

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x, data["bernanke_rule_realtime"], linewidth=2, label="Prescribed rate (real-time gap)")
    ax.plot(x, data["bernanke_rule_today"], linewidth=2, label="Prescribed rate (today's gap)")
    ax.plot(x, data["fedfunds"], linewidth=2, label="Actual federal funds rate")
    shade_recession(ax)
    ax.set(xlabel="Quarters since January 2007", ylabel="Percent")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUT / "chart2_taylor_rule.png", dpi=150)
    plt.close(fig)

    data.to_csv(OUTPUT / "results_table.csv", float_format="%.10f")


if __name__ == "__main__":
    main()
