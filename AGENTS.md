# QAMO5140 — Taylor Rule Analysis Guide

## Purpose

This project reproduces an original Taylor Rule (Taylor, 1993) comparison of the effective federal funds rate with the policy rate prescribed by inflation and the output gap.  The analysis uses downloaded FRED observations, converts the relevant monthly series to quarter-level observations, and produces a reproducible calculation table and chart.

The project deliberately uses the original Taylor Rule specification.  Do not alter the calculations, input data files, date alignment, or rule parameters unless the request explicitly calls for a methodological change.

## FRED source data

The downloaded FRED bundle is stored as `fred_data/fred_raw.csv` (despite the extension, it is a ZIP archive).  Its included `README.txt` records the source metadata and FRED download date.  The extracted input files are:

| Series | FRED identifier | Frequency in download | Use |
| --- | --- | --- | --- |
| Effective federal funds rate | `FEDFUNDS` | Monthly, not seasonally adjusted | Actual policy-rate comparison; quarterly averaged |
| Gross Domestic Product: Implicit Price Deflator | `GDPDEF` | Quarterly, seasonally adjusted | Year-over-year inflation measure |
| Personal Consumption Expenditures Excluding Food and Energy Price Index | `PCEPILFE` | Monthly, seasonally adjusted | Retained in the data/output; not used in the current original-rule calculation |
| Nominal Potential Gross Domestic Product | `NGDPPOT` | Quarterly, not seasonally adjusted | Potential-output denominator |
| Gross Domestic Product | `GDP` | Quarterly, seasonally adjusted annual rate | Actual-output numerator |

The source metadata states that the raw FRED download was created on 2026-08-31.  Observe FRED's terms of use when redistributing or updating its data.

## Taylor Rule specification

The calculation implements John B. Taylor's original 1993 formulation:

```text
i = π + 0.5 × y + 0.5 × (π − π*) + r*
```

Definitions and parameters:

- `i`: prescribed nominal federal funds rate, in percent.
- `π`: four-quarter (year-over-year) GDP-deflator inflation rate, in percent.
- `y`: percentage output gap, `100 × (GDP − NGDPPOT) / NGDPPOT`.
- `π*`: inflation target, 2 percent.
- `r*`: equilibrium real federal funds rate, 2 percent.
- The response coefficient is 0.5 for both the output gap and the inflation gap (`π − π*`).

Thus, `taylor_original` in the output equals `π + 0.5y + 0.5(π − 2) + 2`.  This is the original-rule result; it is not a recommendation, forecast, or estimate of the Federal Reserve's reaction function.

## Data processing and quarterly alignment

`fred_data/analyze_taylor_rule.py` is the authoritative reproducibility script.

1. It reads `monthly.csv` and `quarterly.csv`, parsing `observation_date`.
2. It resamples monthly `FEDFUNDS` and `PCEPILFE` to calendar-quarter starts (`QS`) using the arithmetic mean.
3. A quarterly value is retained only where its individual monthly series has all three observations in that calendar quarter; incomplete quarterly averages are set to missing.
4. It joins those averages to the quarterly GDP, potential-GDP, and GDP-deflator observations by quarter start.
5. It retains only quarters with nonmissing `GDP`, `NGDPPOT`, `GDPDEF`, and `FEDFUNDS`.  This prevents projected `NGDPPOT` values from being represented as observed GDP data.
6. Inflation needs four prior quarters, so early retained quarters have blank `gdpdef_inflation_yoy` and `taylor_original` values.

## Current work and outputs

Completed work consists of the FRED data extraction, the reproducible Python calculation/plot script, the quarter-level output table, and two SVG figures.  The active script calculates and plots the original (1993) Taylor Rule; `fed_funds_vs_modified_taylor_rule.svg` is an existing companion artifact and no corresponding modified-rule calculation is maintained in the current script.

The latest complete calculated quarter in the checked-in output is 2026 Q2 (quarter start 2026-04-01):

- Output gap: 2.316%.
- Average actual effective federal funds rate: 3.633%.
- Original Taylor Rule prescribed rate: 8.716%.

Additional scripted checks in the output are 2009 Q2's output gap (−4.985%) and 2021 Q4's original-rule prescribed rate (11.352%).  The original-rule chart covers 1993 onward and is titled to summarize that the effective federal funds rate has often run below the rule since 2008.

Running the script requires Python with `pandas` installed and will rewrite only its derived files, `taylor_rule_quarterly.csv` and `fed_funds_vs_original_taylor_rule.svg`.  Do not run it if preserving the checked-in artifacts byte-for-byte is necessary.

## Project layout

```text
AGENTS.md                                  Project documentation and maintenance guidance
fred_data/
  README.txt                               FRED download metadata and series descriptions
  fred_raw.csv                             Original FRED ZIP download (extension is misleading)
  monthly.csv                              Extracted monthly FEDFUNDS and PCEPILFE inputs
  quarterly.csv                            Extracted quarterly GDPDEF, NGDPPOT, and GDP inputs
  analyze_taylor_rule.py                   Reproducible data processing, calculation, and SVG export
  taylor_rule_quarterly.csv                Derived quarter-level calculation output
  fed_funds_vs_original_taylor_rule.svg    Actual rate vs. original Taylor Rule figure
  fed_funds_vs_modified_taylor_rule.svg    Existing modified-rule figure artifact
```

## Maintenance constraints

- Treat `fred_raw.csv`, `monthly.csv`, and `quarterly.csv` as source data; do not edit them manually.
- Do not silently substitute PCE inflation for GDP-deflator inflation, or revise the Taylor parameters.
- Preserve calendar-quarter averaging and the complete-quarter rule when updating data.
- If FRED data are refreshed, retain the raw download and update its source metadata alongside regenerated derived outputs.
- Keep any new methodology separate and label its assumptions explicitly rather than overwriting the original-rule series.
