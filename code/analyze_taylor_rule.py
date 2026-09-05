"""Reproduce the output-gap and Taylor-rule calculations from downloaded FRED data."""

from pathlib import Path

import pandas as pd


HERE = Path(__file__).parent


def quarterly_average(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert monthly observations to calendar-quarter averages, retaining full quarters."""
    indexed = frame.set_index("observation_date")
    counts = indexed.resample("QS").count()
    averages = indexed.resample("QS").mean()
    return averages.where(counts.eq(3))


monthly = pd.read_csv(HERE / "monthly.csv", parse_dates=["observation_date"])
quarterly = pd.read_csv(HERE / "quarterly.csv", parse_dates=["observation_date"])

monthly_q = quarterly_average(monthly)
quarterly = quarterly.set_index("observation_date")
data = quarterly.join(monthly_q, how="left")

# Keep only quarters with every series required for the Taylor (1993) rule. This prevents
# NGDPPOT's projection horizon from being treated as observed GDP data.
data = data.dropna(subset=["GDP", "NGDPPOT", "GDPDEF", "FEDFUNDS"])
data["output_gap"] = 100 * (data["GDP"] - data["NGDPPOT"]) / data["NGDPPOT"]
data["gdpdef_inflation_yoy"] = 100 * (data["GDPDEF"] / data["GDPDEF"].shift(4) - 1)
data["taylor_original"] = (
    data["gdpdef_inflation_yoy"]
    + 0.5 * data["output_gap"]
    + 0.5 * (data["gdpdef_inflation_yoy"] - 2)
    + 2
)

data.index.name = "quarter_start"
data.to_csv(HERE / "taylor_rule_quarterly.csv", float_format="%.6f")

latest = data.dropna(subset=["taylor_original"]).iloc[-1]
trough = data.loc[pd.Timestamp("2009-04-01")]
check_2021q4 = data.loc[pd.Timestamp("2021-10-01")]

print(f"Latest quarter: {latest.name:%YQ}{latest.name.quarter}")
print(f"  output gap: {latest.output_gap:.3f}%")
print(f"  actual federal funds rate: {latest.FEDFUNDS:.3f}%")
print(f"  Taylor (1993) prescribed rate: {latest.taylor_original:.3f}%")
print(f"2009Q2 output gap: {trough.output_gap:.3f}%")
print(f"2021Q4 Taylor (1993) rule: {check_2021q4.taylor_original:.3f}%")

plot_data = data.loc["1993-01-01":].dropna(subset=["FEDFUNDS", "taylor_original"])

# Export a dependency-free SVG chart, with title, units, legend, source, and readable dates.
width, height = 1150, 650
left, right, top, bottom = 94, 35, 83, 121
chart_w, chart_h = width - left - right, height - top - bottom
all_values = pd.concat([plot_data["FEDFUNDS"], plot_data["taylor_original"]])
y_min = int(all_values.min() // 2 * 2 - 2)
y_max = int(-(-all_values.max() // 2) * 2 + 2)
x_min, x_max = plot_data.index.min(), plot_data.index.max()

def x_coord(date):
    return left + (date - x_min) / (x_max - x_min) * chart_w

def y_coord(value):
    return top + (y_max - value) / (y_max - y_min) * chart_h

def points(column):
    return " ".join(f"{x_coord(date):.1f},{y_coord(value):.1f}"
                    for date, value in plot_data[column].items())

svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" fill="white"/>',
    '<style>text { font-family: Arial, sans-serif; fill: #202020; } .small { font-size: 13px; } .tick { font-size: 14px; } </style>',
    '<text x="94" y="37" font-size="23" font-weight="bold">The federal funds rate has often run below the original Taylor Rule since 2008</text>',
]
for value in range(y_min, y_max + 1, 2):
    y = y_coord(value)
    svg.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#d9d9d9"/>')
    svg.append(f'<text class="tick" x="{left-12}" y="{y+5:.1f}" text-anchor="end">{value}</text>')
for year in range(1995, x_max.year + 1, 5):
    x = x_coord(pd.Timestamp(f"{year}-01-01"))
    if left <= x <= width - right:
        svg.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{height-bottom}" stroke="#eeeeee"/>')
        svg.append(f'<text class="tick" x="{x:.1f}" y="{height-bottom+25}" text-anchor="middle">{year}</text>')
svg.extend([
    f'<line x1="{left}" x2="{left}" y1="{top}" y2="{height-bottom}" stroke="#555"/>',
    f'<line x1="{left}" x2="{width-right}" y1="{height-bottom}" y2="{height-bottom}" stroke="#555"/>',
    f'<polyline points="{points("FEDFUNDS")}" fill="none" stroke="#1f77b4" stroke-width="2.6"/>',
    f'<polyline points="{points("taylor_original")}" fill="none" stroke="#d62728" stroke-width="2.3"/>',
    f'<text class="tick" x="24" y="{top + chart_h/2:.1f}" transform="rotate(-90 24 {top + chart_h/2:.1f})" text-anchor="middle">Percent (annual rate)</text>',
    '<line x1="112" y1="61" x2="147" y2="61" stroke="#1f77b4" stroke-width="2.6"/>',
    '<text class="small" x="153" y="65">Actual federal funds rate</text>',
    '<line x1="352" y1="61" x2="387" y2="61" stroke="#d62728" stroke-width="2.3"/>',
    '<text class="small" x="393" y="65">Original Taylor Rule (1993)</text>',
    '<text class="small" x="94" y="585">Source: Federal Reserve Bank of St. Louis, FRED: FEDFUNDS, PCEPILFE, GDPDEF, GDP, and NGDPPOT.</text>',
    '<text class="small" x="94" y="605">Quarterly averages for monthly series; author calculations.</text>',
    '</svg>',
])
(HERE / "fed_funds_vs_original_taylor_rule.svg").write_text("\n".join(svg))
