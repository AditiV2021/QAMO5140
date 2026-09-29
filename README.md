# Welfare analysis

This project reproduces the Bernanke-Olson / Jones-Klenow log-lambda calculation from 1979 through 2025, comparing changes in welfare components with changes in ln(GDP per capita). All reported results are changes relative to 1979.

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

FRED download date: 2026-09-29. The local FRED files use chained 2017 dollars; their base year is not adjusted because it cancels in changes in logs. Template parameters are ubar = 5.2325 (`data!AD3`), epsilon = 1 (`data!AD4`), theta = 14.172748 (`data!AD5`), and a 2007 flow-utility normalization (`data!AD6`). 2025 employment and life expectancy are carried forward from 2024 and are provisional. See `AGENTS.md` for the full specification and maintenance rules.
