# QAMO5140 Empirical Exercise 4: Welfare Analysis Guide

## 1. Purpose

This project reproduces and extends the Bernanke-Olson / Jones-Klenow welfare measure, log lambda, from 1979 through 2025. It compares descriptive changes in log lambda with descriptive changes in ln(GDP per capita); the analysis is descriptive.

## 2. Source data

| Series | Source / identifier | Frequency | Use |
|---|---|---|---|
| Real personal consumption expenditures | FRED PCECCA, local `PCECCA.csv`; chained 2017 dollars; downloaded 2026-09-29 | Annual | Core calculation: consumption per capita |
| Real GDP | FRED GDPCA, local `GDPCA.csv`; chained 2017 dollars; downloaded 2026-09-29 | Annual | Core calculation: GDP per capita |
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
- `ubar = 5.2325` (`data!AD3`), `epsilon = 1` (`data!AD4`), and `theta = 14.172748` (`data!AD5`).
- Consumption normalization year = 2007 (`data!AD6`); it is used only inside flow utility.
- Hours endowment = 5,840, embedded in `data!K3:K49`.

## 4. Data processing and alignment

1. The merge key is integer `year`.
2. FRED date fields are converted to integer years; the merged data run from 1979 through 2025 with no gaps.
3. Every reported change has base year 1979 and equals zero there.
4. Population and employment remain in thousands, annual hours remain hours per worker per year, and Gini remains on the 0--1 scale before conversion.
5. Rows with missing core data would be dropped after logging; none were dropped in this run. Unit ambiguity and large log changes are flagged in `verification_log.txt`.

## 5. Verification checks

`analysis.py` asserts component summation, base-year invariance to FRED rescaling, zero 1979 changes, raw-Gini exclusion, and the normal inverse check. It also compares cached template intermediates and writes all results to `verification_log.txt`.

## 6. Current work and outputs

The latest merged year is 2025. Its component changes are life expectancy 0.3715099791, consumption 0.8769854237, leisure -0.0094310002, and inequality -0.1509476320 log points; total log lambda is 1.0881167706 and ln(GDP per capita) is 0.7667844866 log points. The summary uses 1979-2007 and 2007-2025; 2025 employment and life expectancy are carried forward from 2024 and are provisional.

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
