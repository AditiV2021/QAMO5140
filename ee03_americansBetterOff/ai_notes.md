# AI notes

## Session corrections

1. The first workbook scan found blank output columns but did not extract the embedded equation images. The user supplied the equations and `xl/media/image2.png` was subsequently identified as the leisure-value equation.
2. The supplied offline runtime does not include SciPy. The calculation uses Python's standard-library `statistics.NormalDist.inv_cdf` for the specified normal inverse; it does not alter the formula.
3. The first full-script execution selected the 1979 base row before flow-utility columns existed. The calculation now refreshes the base row after those columns are constructed; no formula or input was changed.

## Parameters and template references

- `UBAR = 5.2325` from `data!AD3`.
- `EPSILON = 1` from `data!AD4`.
- `THETA = 14.172748` from `data!AD5`.
- `NORMALIZATION_YEAR = 2007` from `data!AD6`.
- `HOURS_ENDOWMENT = 5,840` from the literal `365*16` in `data!K3:K49`.
- Hours per person is `data!J3:J49`; leisure is `data!K3:K49`; Gini conversion is `data!N3:N49`.

## Source/template differences and uncertainties

- The template has no cached values in component/output columns `P:AA`; a component-level maximum replication difference is therefore unavailable.
- The maximum cached-intermediate differences using the Stata input are J = 6.56988859191e-05 (year 2021), K = 1.12498091953e-08 (year 2021), and N = 0.00409658814164 (year 2025).
- Template Gini values differ from the Stata input in 2024 (template 0.489; Stata 0.488) and 2025 (template 0.490; Stata 0.489). The script uses Stata Gini throughout.
- The template notes state that 2025 employment and life expectancy are carried forward from 2024; the script uses the Stata values throughout and flags 2025 as provisional.
