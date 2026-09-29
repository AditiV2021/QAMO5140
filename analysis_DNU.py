#!/usr/bin/env python3
"""Reproduce the Bernanke-Olson / Jones-Klenow welfare calculation locally."""

from __future__ import annotations

import base64
import csv
import html
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFont

# ---- Configurable local inputs and template constants ----
PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = Path("/Users/aditi/Downloads")
STATA_PATH = INPUT_DIR / "bernanke_olson_inputs.dta"
PCE_PATH = INPUT_DIR / "PCECCA.csv"
GDP_PATH = INPUT_DIR / "GDPCA.csv"
TEMPLATE_PATH = INPUT_DIR / "Bernanke Olson Welfare Blank.xlsx"
FRED_DOWNLOAD_DATE = "2026-09-29"

BASE_YEAR = 1979
NORMALIZATION_YEAR = 2007  # Template cell data!AD6; used only in flow utility.
UBAR = 5.2325             # Template cell data!AD3.
EPSILON = 1.0             # Template cell data!AD4.
THETA = 14.172748         # Template cell data!AD5.
HOURS_ENDOWMENT = 365.0 * 16.0  # Embedded in template cells data!K3:K49.
JUMP_THRESHOLD_LOG_POINTS = 5.0
PROVISIONAL_YEAR = 2025

RESULTS_PATH = PROJECT_DIR / "results_by_year.csv"
SUMMARY_PATH = PROJECT_DIR / "summary_tables.csv"
CHECK_BLOCK_PATH = PROJECT_DIR / "template_check_block.csv"
VERIFY_PATH = PROJECT_DIR / "verification_log.txt"
FINAL_PNG = PROJECT_DIR / "final_chart.png"
FINAL_HTML = PROJECT_DIR / "final_chart.html"
DIAGNOSTICS_DIR = PROJECT_DIR / "diagnostics"

NORMAL = NormalDist()
LOG_LINES: list[str] = []


def emit(message: str = "") -> None:
    """Print and retain verification information."""
    print(message)
    LOG_LINES.append(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    emit(f"PASS: {message}")


def read_fred(path: Path, value_column: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    date_column = next(
        (column for column in frame.columns if column.lower() in {"observation_date", "date"}),
        None,
    )
    if date_column is None:
        raise ValueError(f"{path.name} has no observation_date or DATE column.")
    if value_column not in frame.columns:
        raise ValueError(f"{path.name} has no {value_column} column.")
    frame = frame[[date_column, value_column]].copy()
    frame["year"] = pd.to_datetime(frame[date_column], errors="raise").dt.year.astype(int)
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna(subset=[value_column]).drop_duplicates("year", keep="last")
    return frame[["year", value_column]]


def normal_inverse(probability: float) -> float:
    """Standard-library replacement for scipy.stats.norm.ppf."""
    return NORMAL.inv_cdf(float(probability))


def value_of_leisure(leisure: pd.Series | np.ndarray) -> pd.Series | np.ndarray:
    return -(THETA * EPSILON / (1.0 + EPSILON)) * (1.0 - leisure) ** ((1.0 + EPSILON) / EPSILON)


def calculate(frame: pd.DataFrame, pce_scale: float = 1.0, gdp_scale: float = 1.0) -> pd.DataFrame:
    """Compute template intermediates and final changes, all relative to BASE_YEAR."""
    data = frame.copy()
    data["PCE_scaled"] = data["PCECCA"] * pce_scale
    data["GDP_scaled"] = data["GDPCA"] * gdp_scale
    data["hours_per_person"] = data["hours"] * data["employment"] / data["pop"]
    data["leisure"] = 1.0 - data["hours_per_person"] / HOURS_ENDOWMENT
    data["consumption_per_capita"] = data["PCE_scaled"] / data["pop"]
    data["gdp_per_capita"] = data["GDP_scaled"] / data["pop"]
    data["variance_log_consumption"] = (
        np.sqrt(2.0)
        * np.array([normal_inverse((gini + 1.0) / 2.0) for gini in data["gini"]], dtype=float)
    ) ** 2

    base = data.loc[data["year"] == BASE_YEAR].iloc[0]
    normalized = data.loc[data["year"] == NORMALIZATION_YEAR].iloc[0]
    data["consumption_relative_to_2007"] = data["consumption_per_capita"] / normalized["consumption_per_capita"]
    data["log_consumption_relative_to_2007"] = np.log(data["consumption_relative_to_2007"])
    data["leisure_value"] = value_of_leisure(data["leisure"])
    data["inequality_flow"] = -0.5 * data["variance_log_consumption"]
    data["flow_utility"] = UBAR + data["log_consumption_relative_to_2007"] + data["leisure_value"] + data["inequality_flow"]

    # Refresh the base row after calculated columns have been added.
    base = data.loc[data["year"] == BASE_YEAR].iloc[0]
    data["life_expectancy_change"] = (
        (data["expectancy"] - base["expectancy"]) / base["expectancy"] * data["flow_utility"]
    )
    data["consumption_change"] = np.log(data["consumption_per_capita"]) - np.log(base["consumption_per_capita"])
    data["leisure_change"] = data["leisure_value"] - base["leisure_value"]
    data["inequality_change"] = data["inequality_flow"] - base["inequality_flow"]
    data["log_lambda_change"] = (
        data["life_expectancy_change"]
        + data["consumption_change"]
        + data["leisure_change"]
        + data["inequality_change"]
    )
    data["ln_gdp_per_capita_change"] = np.log(data["gdp_per_capita"]) - np.log(base["gdp_per_capita"])
    return data


def template_intermediate_check(calculated: pd.DataFrame) -> dict[str, float | str]:
    """Compare nonblank cached template intermediates without changing source inputs."""
    book = load_workbook(TEMPLATE_PATH, data_only=True)
    sheet = book["data"]
    checks = {
        "J_hours_per_person": ("hours_per_person", 10),
        "K_leisure": ("leisure", 11),
        "N_variance_log_consumption": ("variance_log_consumption", 14),
    }
    outcome: dict[str, float | str] = {}
    for label, (column, template_column) in checks.items():
        cached = np.array(
            [sheet.cell(row=index + 3, column=template_column).value for index in range(len(calculated))],
            dtype=float,
        )
        differences = np.abs(calculated[column].to_numpy(dtype=float) - cached)
        maximum_index = int(np.argmax(differences))
        outcome[f"{label}_max_abs_difference"] = float(differences[maximum_index])
        outcome[f"{label}_max_difference_year"] = int(calculated.iloc[maximum_index]["year"])
    cached_component_cells = sum(
        cell.value is not None
        for row in sheet.iter_rows(min_row=3, max_row=49, min_col=16, max_col=27)
        for cell in row
    )
    outcome["cached_component_output_cells"] = int(cached_component_cells)
    outcome["component_output_max_abs_difference"] = (
        "unavailable: blank template output cells" if cached_component_cells == 0 else "not implemented"
    )
    return outcome


def period_row(data: pd.DataFrame, start: int, end: int, label: str) -> dict[str, float | str | int]:
    start_row = data.loc[data["year"] == start].iloc[0]
    end_row = data.loc[data["year"] == end].iloc[0]
    component_columns = ["life_expectancy_change", "consumption_change", "leisure_change", "inequality_change"]
    values = {column: float(end_row[column] - start_row[column]) for column in component_columns}
    total = float(end_row["log_lambda_change"] - start_row["log_lambda_change"])
    gdp = float(end_row["ln_gdp_per_capita_change"] - start_row["ln_gdp_per_capita_change"])
    years = end - start
    row: dict[str, float | str | int] = {"period": label, "start_year": start, "end_year": end, "years": years}
    row.update(values)
    row["total_log_lambda_change"] = total
    row["ln_gdp_per_capita_change"] = gdp
    for column, value in values.items():
        row[f"{column}_share_of_total"] = value / total if total != 0 else np.nan
    row["log_lambda_average_annual_growth_percent"] = total / years * 100.0 if years else np.nan
    row["ln_gdp_per_capita_average_annual_growth_percent"] = gdp / years * 100.0 if years else np.nan
    return row


def write_charts(data: pd.DataFrame) -> None:
    DIAGNOSTICS_DIR.mkdir(exist_ok=True)
    components = {
        "life_expectancy_change": "Life expectancy",
        "consumption_change": "Consumption",
        "leisure_change": "Leisure",
        "inequality_change": "Inequality",
    }
    def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()

    def draw_line_chart(series: list[tuple[str, str, str]], title: str, output: Path, source_note: str | None = None) -> None:
        width, height = 1800, 1100
        left, top, right, bottom = 180, 120, 1710, 900
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        title_font, body_font, small_font = font(38, True), font(25), font(20)
        all_values = np.concatenate([data[column].to_numpy(dtype=float) for column, _, _ in series] + [np.array([0.0])])
        y_min, y_max = float(all_values.min()), float(all_values.max())
        padding = max((y_max - y_min) * 0.12, 0.02)
        y_min, y_max = y_min - padding, y_max + padding
        if y_max == y_min:
            y_min, y_max = -0.1, 0.1
        years = data["year"].to_numpy(dtype=float)
        x_min, x_max = float(years.min()), float(years.max())
        x_coord = lambda year: left + (year - x_min) / (x_max - x_min) * (right - left)
        y_coord = lambda value: bottom - (value - y_min) / (y_max - y_min) * (bottom - top)
        draw.text((left, 40), title, fill="#111827", font=title_font)
        # Round ("nice") y-axis ticks so that 0 is an exact gridline and labels are not misleading.
        raw_step = (y_max - y_min) / 6
        magnitude = 10 ** np.floor(np.log10(raw_step))
        multiple = next(m for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw_step)
        step = multiple * magnitude
        decimals = max(0, int(-np.floor(np.log10(step))) + (1 if multiple == 2.5 else 0))
        first_tick = np.ceil(y_min / step - 1e-9) * step
        tick_count = int(np.floor((y_max - first_tick) / step + 1e-9)) + 1
        for k in range(tick_count):
            tick = round(float(first_tick + k * step), 10) + 0.0
            y = y_coord(tick)
            draw.line((left, y, right, y), fill="#d1d5db", width=2)
            draw.text((25, y - 12), f"{tick:.{decimals}f}", fill="#374151", font=small_font)
        # Ticks every 5 years; drop any tick within 3 years of the last year so labels do not overlap.
        x_ticks = [t for t in range(int(x_min), int(x_max) + 1, 5) if int(x_max) - t >= 3] + [int(x_max)]
        for tick in x_ticks:
            x = x_coord(tick)
            draw.line((x, top, x, bottom), fill="#eef2f7", width=1)
            draw.text((x - 24, bottom + 18), str(tick), fill="#374151", font=small_font)
        zero_y = y_coord(0.0)
        draw.line((left, zero_y, right, zero_y), fill="#4b5563", width=2)
        draw.line((left, top, left, bottom), fill="#111827", width=3)
        draw.line((left, bottom, right, bottom), fill="#111827", width=3)
        for column, label, color in series:
            points = [(x_coord(year), y_coord(value)) for year, value in zip(years, data[column].to_numpy(dtype=float))]
            draw.line(points, fill=color, width=5, joint="curve")
        draw.text((right - 185, bottom + 65), "Year", fill="#111827", font=body_font)
        draw.text((left, top - 42), "Change relative to 1979 (log points)", fill="#111827", font=body_font)
        legend_x, legend_y = left + 15, top + 15
        for _, label, color in series:
            draw.line((legend_x, legend_y + 14, legend_x + 45, legend_y + 14), fill=color, width=5)
            draw.text((legend_x + 58, legend_y), label, fill="#111827", font=small_font)
            legend_y += 34
        if source_note:
            draw.text((left, height - 75), source_note, fill="#4b5563", font=small_font)
        image.save(output, dpi=(250, 250))

    draw_line_chart(
        [("log_lambda_change", "Change in log lambda", "#1d4ed8"), ("ln_gdp_per_capita_change", "Change in ln(GDP per capita)", "#c2410c")],
        "U.S. welfare and GDP per capita changes since 1979",
        FINAL_PNG,
        "Sources: local FRED PCECCA and GDPCA; bernanke_olson_inputs.dta. FRED download: 2026-09-29.",
    )
    for column, label in components.items():
        draw_line_chart([(column, label, "#1d4ed8")], f"{label} component since 1979", DIAGNOSTICS_DIR / f"{column}.png")
    draw_line_chart(
        [(column, label, color) for (column, label), color in zip(components.items(), ["#2563eb", "#16a34a", "#9333ea", "#dc2626"])]
        + [("log_lambda_change", "Total log lambda", "#111827")],
        "Welfare components and total change since 1979",
        DIAGNOSTICS_DIR / "components_and_total.png",
    )

    encoded = base64.b64encode(FINAL_PNG.read_bytes()).decode("ascii")
    FINAL_HTML.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Welfare and GDP chart</title></head>"
        "<body><img alt='Change in log lambda and ln GDP per capita since 1979' style='max-width:100%;height:auto' "
        f"src='data:image/png;base64,{encoded}'></body></html>",
        encoding="utf-8",
    )


def write_documentation(results: pd.DataFrame, summary: pd.DataFrame, template_check: dict[str, float | str]) -> None:
    latest = results.iloc[-1]
    latest_year = int(latest["year"])
    s79_latest = summary.loc[summary["period"] == f"{BASE_YEAR}-{latest_year}"].iloc[0]
    agents = f"""# QAMO5140 Empirical Exercise 4: Welfare Analysis Guide

## 1. Purpose

This project reproduces and extends the Bernanke-Olson / Jones-Klenow welfare measure, log lambda, from 1979 through {latest_year}. It compares descriptive changes in log lambda with descriptive changes in ln(GDP per capita); the analysis is descriptive.

## 2. Source data

| Series | Source / identifier | Frequency | Use |
|---|---|---|---|
| Real personal consumption expenditures | FRED PCECCA, local `PCECCA.csv`; chained 2017 dollars; downloaded {FRED_DOWNLOAD_DATE} | Annual | Core calculation: consumption per capita |
| Real GDP | FRED GDPCA, local `GDPCA.csv`; chained 2017 dollars; downloaded {FRED_DOWNLOAD_DATE} | Annual | Core calculation: GDP per capita |
| Life expectancy | `bernanke_olson_inputs.dta`, `expectancy` | Annual | Core calculation: life-expectancy component |
| Population | `bernanke_olson_inputs.dta`, `pop` | Annual | Core calculation: per-capita and leisure measures; thousands of persons |
| Employment | `bernanke_olson_inputs.dta`, `employment` | Annual | Core calculation: leisure measure; thousands of persons |
| Annual hours per worker | `bernanke_olson_inputs.dta`, `hours` | Annual | Core calculation: leisure measure; hours per worker per year |
| Gini coefficient | `bernanke_olson_inputs.dta`, `gini` | Annual | Core calculation: converted to variance of log consumption |
| Income detail | `CBO_income_detail.csv` | Annual | Context only; not used in the core calculation |

## 3. Welfare specification

All results are changes relative to 1979 in log points.

```text
U_t = ((e_t - e_1979) / e_1979) * (ubar + ln(c_t/c_2007) + v(l_t) - sigma2_t/2)
V_t = ln(c_t) - ln(c_1979)
W_t = v(l_t) - v(l_1979)
X_t = -0.5 * (sigma2_t - sigma2_1979)
Y_t = U_t + V_t + W_t + X_t
v(l) = -(theta * epsilon / (1 + epsilon)) * (1-l)^((1+epsilon)/epsilon)
```

- `e`: raw life expectancy in years.
- `c`: real PCE per person.
- `l`: `1 - (hours * employment / population) / 5840`, from `data!J3:J49` and `data!K3:K49`.
- `sigma2`: `(sqrt(2) * Phi^-1((gini + 1)/2))^2`, from `data!N3:N49`; raw Gini is not used directly.
- `ubar = {UBAR}` (`data!AD3`), `epsilon = {EPSILON:g}` (`data!AD4`), and `theta = {THETA}` (`data!AD5`).
- Consumption normalization year = {NORMALIZATION_YEAR} (`data!AD6`); it is used only inside flow utility.
- Hours endowment = {HOURS_ENDOWMENT:,.0f}, embedded in `data!K3:K49`.

## 4. Data processing and alignment

1. The merge key is integer `year`.
2. FRED date fields are converted to integer years; the merged data run from {BASE_YEAR} through {latest_year} with no gaps.
3. Every reported change has base year {BASE_YEAR} and equals zero there.
4. Population and employment remain in thousands, annual hours remain hours per worker per year, and Gini remains on the 0--1 scale before conversion.
5. Rows with missing core data would be dropped after logging; none were dropped in this run. Unit ambiguity and large log changes are flagged in `verification_log.txt`.

## 5. Verification checks

`analysis.py` asserts component summation, base-year invariance to FRED rescaling, zero 1979 changes, raw-Gini exclusion, and the normal inverse check. It also compares cached template intermediates and writes all results to `verification_log.txt`.

## 6. Current work and outputs

The latest merged year is {latest_year}. Its component changes are life expectancy {latest['life_expectancy_change']:.10f}, consumption {latest['consumption_change']:.10f}, leisure {latest['leisure_change']:.10f}, and inequality {latest['inequality_change']:.10f} log points; total log lambda is {latest['log_lambda_change']:.10f} and ln(GDP per capita) is {latest['ln_gdp_per_capita_change']:.10f} log points. The summary uses {BASE_YEAR}-2007 and 2007-{latest_year}; {PROVISIONAL_YEAR} employment and life expectancy are carried forward from {PROVISIONAL_YEAR - 1} and are provisional.

## 7. Project layout

```text
AGENTS.md                 project specification and maintenance rules
analysis.py               reproducible analysis script
README.md                 setup and output guide
results_by_year.csv       annual welfare-component results
summary_tables.csv        latest-year and subperiod summaries
template_check_block.csv  replicated template-style check block
final_chart.png           submitted comparison chart
final_chart.html          embeddable comparison chart
diagnostics/              component diagnostic charts
verification_log.txt      automated-check output
ai_notes.md               methodology and session notes
```

## 8. Maintenance constraints

- Treat raw input files (`.dta`, CBO file, template, and FRED CSVs) as source data; never edit them manually.
- Do not correct the chained-dollar base year; it cancels in changes in logs.
- Do not use the Gini directly as the variance of log consumption.
- Report changes in logs, not levels, and label units as log points.
- Do not change template parameters or formulas without an explicit request; keep any new methodology separate and label its assumptions.
- If FRED data are refreshed, re-download the CSVs manually, keep the old files, update the download date, and regenerate all derived outputs.
- Rerunning `analysis.py` overwrites the derived files listed in the layout; do not run it if checked-in artifacts must be preserved byte-for-byte.
"""
    (PROJECT_DIR / "AGENTS.md").write_text(agents, encoding="utf-8")

    readme = f"""# Welfare analysis

This project reproduces the Bernanke-Olson / Jones-Klenow log-lambda calculation from 1979 through {latest_year}, comparing changes in welfare components with changes in ln(GDP per capita). All reported results are changes relative to 1979.

## Requirements

Python 3.12 or later with `pandas`, `numpy`, `openpyxl`, and `Pillow`. The normal inverse uses Python's built-in `statistics.NormalDist.inv_cdf` because SciPy is unavailable in the supplied offline runtime. Pillow renders the charts because Matplotlib is unavailable in the supplied offline runtime.

## Run

Place `bernanke_olson_inputs.dta`, `PCECCA.csv`, `GDPCA.csv`, and `Bernanke Olson Welfare Blank.xlsx` in the directory configured by `INPUT_DIR` at the top of `analysis.py` (default: `/Users/aditi/Downloads`). Then run:

```bash
/Users/aditi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 analysis.py
```

## Inputs and outputs

The Stata and FRED files are core inputs. `CBO_income_detail.csv` is context only. The script writes `results_by_year.csv`, `summary_tables.csv`, `template_check_block.csv`, `final_chart.png`, `final_chart.html`, `diagnostics/`, `verification_log.txt`, and `ai_notes.md`. A passing run prints `PASS` for each assertion and writes the same check record to `verification_log.txt`.

## Reproducibility

FRED download date: {FRED_DOWNLOAD_DATE}. The local FRED files use chained 2017 dollars; their base year is not adjusted because it cancels in changes in logs. Template parameters are ubar = {UBAR} (`data!AD3`), epsilon = {EPSILON:g} (`data!AD4`), theta = {THETA} (`data!AD5`), and a 2007 flow-utility normalization (`data!AD6`). {PROVISIONAL_YEAR} employment and life expectancy are carried forward from {PROVISIONAL_YEAR - 1} and are provisional. See `AGENTS.md` for the full specification and maintenance rules.
"""
    (PROJECT_DIR / "README.md").write_text(readme, encoding="utf-8")

    notes = f"""# AI notes

## Session corrections

1. The first workbook scan found blank output columns but did not extract the embedded equation images. The user supplied the equations and `xl/media/image2.png` was subsequently identified as the leisure-value equation.
2. The supplied offline runtime does not include SciPy. The calculation uses Python's standard-library `statistics.NormalDist.inv_cdf` for the specified normal inverse; it does not alter the formula.
3. The first full-script execution selected the 1979 base row before flow-utility columns existed. The calculation now refreshes the base row after those columns are constructed; no formula or input was changed.

## Parameters and template references

- `UBAR = {UBAR}` from `data!AD3`.
- `EPSILON = {EPSILON:g}` from `data!AD4`.
- `THETA = {THETA}` from `data!AD5`.
- `NORMALIZATION_YEAR = {NORMALIZATION_YEAR}` from `data!AD6`.
- `HOURS_ENDOWMENT = {HOURS_ENDOWMENT:,.0f}` from the literal `365*16` in `data!K3:K49`.
- Hours per person is `data!J3:J49`; leisure is `data!K3:K49`; Gini conversion is `data!N3:N49`.

## Source/template differences and uncertainties

- The template has no cached values in component/output columns `P:AA`; a component-level maximum replication difference is therefore unavailable.
- The maximum cached-intermediate differences using the Stata input are J = {template_check['J_hours_per_person_max_abs_difference']:.12g} (year {template_check['J_hours_per_person_max_difference_year']}), K = {template_check['K_leisure_max_abs_difference']:.12g} (year {template_check['K_leisure_max_difference_year']}), and N = {template_check['N_variance_log_consumption_max_abs_difference']:.12g} (year {template_check['N_variance_log_consumption_max_difference_year']}).
- Template Gini values differ from the Stata input in 2024 (template 0.489; Stata 0.488) and 2025 (template 0.490; Stata 0.489). The script uses Stata Gini throughout.
- The template notes state that {PROVISIONAL_YEAR} employment and life expectancy are carried forward from {PROVISIONAL_YEAR - 1}; the script uses the Stata values throughout and flags {PROVISIONAL_YEAR} as provisional.
"""
    (PROJECT_DIR / "ai_notes.md").write_text(notes, encoding="utf-8")


def main() -> None:
    for path in (STATA_PATH, PCE_PATH, GDP_PATH, TEMPLATE_PATH):
        if not path.exists():
            raise FileNotFoundError(path)
    DIAGNOSTICS_DIR.mkdir(exist_ok=True)

    stata = pd.read_stata(STATA_PATH)
    require(set(["year", "expectancy", "pop", "employment", "hours", "gini"]).issubset(stata.columns), "Stata input has all required columns")
    pce = read_fred(PCE_PATH, "PCECCA")
    gdp = read_fred(GDP_PATH, "GDPCA")
    merged = stata.merge(pce, on="year", how="inner", validate="one_to_one").merge(gdp, on="year", how="inner", validate="one_to_one")
    merged = merged.loc[(merged["year"] >= BASE_YEAR)].sort_values("year").reset_index(drop=True)
    latest_year = int(merged["year"].max())
    expected_years = set(range(BASE_YEAR, latest_year + 1))
    require(set(merged["year"]) == expected_years, f"merged years are complete from {BASE_YEAR} through {latest_year}")
    require(not merged.isna().any().any(), "merged core input has no missing values")
    require((merged["gini"] > 0).all() and (merged["gini"] < 1).all(), "Gini is on the 0-1 scale")
    require((merged["pop"] > 1000).all() and (merged["employment"] > 1000).all(), "population and employment are in thousands")
    require((merged["hours"] > 1000).all() and (merged["hours"] < 3000).all(), "hours are annual hours per worker")

    data = calculate(merged)
    require(math.isclose(normal_inverse(0.975), 1.959963984540054, rel_tol=0.0, abs_tol=1e-12), "inv_cdf(0.975) equals 1.959964 to tolerance")
    require(np.allclose(data["hours_per_person"], data["hours"] * data["employment"] / data["pop"], atol=0.0, rtol=0.0), "hours per person equals hours times employment divided by population")
    require(np.allclose(data["leisure"], 1.0 - data["hours_per_person"] / HOURS_ENDOWMENT, atol=0.0, rtol=0.0), "leisure equals 1 minus hours per person divided by 5840")
    require(not np.allclose(data["variance_log_consumption"], data["gini"]), "raw Gini is not used directly as variance")
    require(np.allclose(data.loc[data["year"] == BASE_YEAR, ["life_expectancy_change", "consumption_change", "leisure_change", "inequality_change", "log_lambda_change", "ln_gdp_per_capita_change"]], 0.0, atol=0.0, rtol=0.0), "all final changes equal exactly zero in 1979")
    sum_difference = data["life_expectancy_change"] + data["consumption_change"] + data["leisure_change"] + data["inequality_change"] - data["log_lambda_change"]
    max_sum_difference = float(np.abs(sum_difference).max())
    require(max_sum_difference <= 1e-10, f"components sum to total in every year; max absolute difference {max_sum_difference:.12g}")

    scaled = calculate(merged, pce_scale=1.37, gdp_scale=1.37)
    change_columns = ["life_expectancy_change", "consumption_change", "leisure_change", "inequality_change", "log_lambda_change", "ln_gdp_per_capita_change"]
    invariance_max = float(np.abs(data[change_columns].to_numpy() - scaled[change_columns].to_numpy()).max())
    require(invariance_max <= 1e-10, f"base-year invariance after 1.37 rescaling; max absolute difference {invariance_max:.12g}")

    template_check = template_intermediate_check(data)
    emit("TEMPLATE REPLICATION (2007 normalization inside flow utility):")
    for key, value in template_check.items():
        emit(f"  {key}: {value}")
    emit("Template component/output comparison is unavailable because P:AA cached values are blank.")

    row_2007 = data.loc[data["year"] == 2007].iloc[0]
    emit("2007 STEP BY STEP:")
    for column in [
        "expectancy", "pop", "employment", "hours", "gini", "PCECCA", "GDPCA", "hours_per_person", "leisure",
        "consumption_per_capita", "gdp_per_capita", "variance_log_consumption", "consumption_relative_to_2007",
        "log_consumption_relative_to_2007", "leisure_value", "inequality_flow", "flow_utility", "life_expectancy_change",
        "consumption_change", "leisure_change", "inequality_change", "log_lambda_change", "ln_gdp_per_capita_change",
    ]:
        emit(f"  {column}: {row_2007[column]:.12g}")

    jumps = []
    for column in change_columns:
        differences = data[column].diff().abs()
        for index in data.index[differences > JUMP_THRESHOLD_LOG_POINTS]:
            jumps.append((int(data.loc[index, "year"]), column, float(differences.loc[index])))
    emit(f"JUMPS > {JUMP_THRESHOLD_LOG_POINTS:g} log points: {jumps if jumps else 'none'}")

    output_columns = [
        "year", "life_expectancy_change", "consumption_change", "leisure_change", "inequality_change", "log_lambda_change", "ln_gdp_per_capita_change",
        "hours_per_person", "leisure", "variance_log_consumption", "flow_utility",
    ]
    data[output_columns].to_csv(RESULTS_PATH, index=False, float_format="%.12f")
    periods = [
        (BASE_YEAR, 2007, f"{BASE_YEAR}-2007"),
        (BASE_YEAR, latest_year, f"{BASE_YEAR}-{latest_year}"),
        (2007, latest_year, f"2007-{latest_year}"),
        (1995, 2007, "1995-2007"),
        (2007, 2015, "2007-2015"),
    ]
    summary = pd.DataFrame([period_row(data, start, end, label) for start, end, label in periods])
    summary.to_csv(SUMMARY_PATH, index=False, float_format="%.12f")

    check_rows = []
    for start, end, label in periods[:3]:
        item = period_row(data, start, end, label)
        check_rows.append({
            "period": label,
            "life_expectancy": item["life_expectancy_change"],
            "consumption": item["consumption_change"],
            "leisure": item["leisure_change"],
            "inequality": item["inequality_change"],
            "log_lambda": item["total_log_lambda_change"],
            "ln_gdp_per_capita": item["ln_gdp_per_capita_change"],
        })
    check_rows.extend([
        {"period": f"Average annual growth, percent per year: {BASE_YEAR}-2007", **{key: value / 28.0 * 100.0 for key, value in check_rows[0].items() if key != "period"}},
        {"period": f"Average annual growth, percent per year: 2007-{latest_year}", **{key: value / (latest_year - 2007) * 100.0 for key, value in check_rows[2].items() if key != "period"}},
    ])
    pd.DataFrame(check_rows).to_csv(CHECK_BLOCK_PATH, index=False, float_format="%.12f")

    write_charts(data)
    write_documentation(pd.read_csv(RESULTS_PATH), pd.read_csv(SUMMARY_PATH), template_check)
    VERIFY_PATH.write_text("\n".join(LOG_LINES) + "\n", encoding="utf-8")

    emit("SUMMARY TABLE:")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.8f}"))
    emit(f"Wrote {RESULTS_PATH.name}, {SUMMARY_PATH.name}, {CHECK_BLOCK_PATH.name}, charts, documentation, and verification log.")
    VERIFY_PATH.write_text("\n".join(LOG_LINES) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
    
