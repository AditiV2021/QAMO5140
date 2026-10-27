"""Rebuild the Exercise 6 deliverables from output/slack_measures.csv only."""
from pathlib import Path
import base64
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
RESULTS = OUT / "slack_measures.csv"
required = ["date", "U3_official", "U1_long_term", "LFPR"]
data = pd.read_csv(RESULTS, parse_dates=["date"])
missing = sorted(set(required) - set(data.columns))
if missing:
    raise ValueError(f"Monthly results are missing required columns: {missing}")
data = data[required].sort_values("date").set_index("date")
data = data.loc[data.index >= "2015-01-01"]
# Keep only the three assigned measures in the monthly output.
data.round(2).to_csv(RESULTS, index_label="date")

# Two-panel chart: U-3 and U-1 share the top axis; LFPR has its own scale.
W, H = 1400, 980
im = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(im)
try:
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 19)
    titlefont = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 25)
except OSError:
    small = medium = titlefont = ImageFont.load_default()

dates = data.index
left, right = 115, 1340
series_colors = {"U3_official": "#1769aa", "U1_long_term": "#d1495b", "LFPR": "#23856d"}
grid, axis, shade = "#d9d9d9", "#333333", "#eeeeee"

def panel(title, top, bottom, columns, ymin, ymax, yticks, ylabel):
    draw.text((left, top), title, fill="#111111", font=titlefont)
    graph_top, graph_bottom = top + 64, bottom - 38
    def xy(i, val):
        x = left + 55 + i * (right - left - 70) / max(1, len(dates) - 1)
        y = graph_bottom - (val - ymin) / (ymax - ymin) * (graph_bottom - graph_top)
        return int(x), int(y)
    march = dates.get_indexer([pd.Timestamp("2020-03-01")])[0]
    june = dates.get_indexer([pd.Timestamp("2020-06-01")])[0]
    if march >= 0 and june >= 0:
        x1, _ = xy(march, ymin)
        x2, _ = xy(june, ymin)
        draw.rectangle((x1, graph_top, x2, graph_bottom), fill=shade)
    for tick in yticks:
        _, y = xy(0, tick)
        draw.line((left + 55, y, right, y), fill=grid, width=1)
        draw.text((left, y - 10), f"{tick:g}%", fill="#444444", font=small)
    draw.line((left + 55, graph_top, left + 55, graph_bottom), fill=axis, width=2)
    draw.line((left + 55, graph_bottom, right, graph_bottom), fill=axis, width=2)
    label_layer = Image.new("RGBA", (280, 28), (255, 255, 255, 0))
    ImageDraw.Draw(label_layer).text((0, 0), ylabel, fill="#333333", font=small)
    label_layer = label_layer.rotate(90, expand=True)
    label_y = graph_top + (graph_bottom - graph_top - label_layer.height) // 2
    im.paste(label_layer, (18, label_y), label_layer)
    for j, date in enumerate(dates):
        if date.month == 1:
            x, _ = xy(j, ymin)
            draw.text((x - 22, graph_bottom + 7), str(date.year), fill="#444444", font=small)
    lx, ly = left + 68, top + 34
    for col, label in columns:
        color = series_colors[col]
        draw.line((lx, ly + 11, lx + 32, ly + 11), fill=color, width=4)
        draw.text((lx + 40, ly), label, fill="#222222", font=medium)
        vals = data[col].to_numpy()
        points = [xy(i, val) for i, val in enumerate(vals) if np.isfinite(val)]
        if len(points) > 1:
            draw.line(points, fill=color, width=4)
        lx += 400

panel("Unemployment rates", 35, 480,
      [("U3_official", "U-3 (official)"),
       ("U1_long_term", "U-1 (unemployed 15+ weeks)")],
      0, 18, [0, 5, 10, 15], "Percent of labor force")
panel("Labor force participation", 505, 910,
      [("LFPR", "LFPR (ages 16+)")],
      59, 65, [59, 61, 63, 65], "Percent of population")
draw.text((left, 943),
          "Source: IPUMS CPS basic monthly extract, weighted with WTFINL. Gray shading: March-May 2020.",
          fill="#444444", font=small)
im.save(OUT / "slack_chart.png")

last_date = data.index.max()
avg19 = data.loc["2019"].mean()
feb = data.loc[pd.Timestamp("2020-02-01")]
april = data.loc[pd.Timestamp("2020-04-01")]
latest = data.loc[last_date]
periods = [("2019 average", avg19), ("Feb 2020", feb), ("April 2020", april),
           (f"Latest ({last_date:%b %Y})", latest)]
labels = {"U3_official": "U-3", "U1_long_term": "U-1", "LFPR": "LFPR"}
table = pd.DataFrame(
    [[f"{row[c]:.2f}%" for c in required[1:]] for _, row in periods],
    index=[name for name, _ in periods], columns=[labels[c] for c in required[1:]])

answer = (
    f"By {last_date:%B %Y}, U-3 was {latest.U3_official:.2f}%, near February 2020's {feb.U3_official:.2f}% "
    f"and the 2019 average of {avg19.U3_official:.2f}%, consistent with broad recovery. U-1 was "
    f"{latest.U1_long_term:.2f}%, just {latest.U1_long_term-feb.U1_long_term:.2f} percentage points above "
    f"February 2020 and {latest.U1_long_term-avg19.U1_long_term:.2f} percentage points above 2019, "
    f"so it signals little remaining "
    f"long-term unemployment slack. LFPR was {latest.LFPR:.2f}%, {feb.LFPR-latest.LFPR:.2f} points below "
    f"February 2020 and {avg19.LFPR-latest.LFPR:.2f} below 2019; population aging may explain part of the gap. "
    "U-1 agrees with U-3, while LFPR is a slightly softer signal, illustrating Gilchrist and Hobijn's point that "
    "slack measures can diverge.")

table_html = table.to_html(classes="data", border=0)
chart_b64 = base64.b64encode((OUT / "slack_chart.png").read_bytes()).decode("ascii")
html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Alternative measures of unemployment</title>
<style>body{{font-family:Arial,sans-serif;max-width:900px;margin:2rem auto;line-height:1.45;color:#222}}
img{{width:100%;height:auto}}table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:.35rem .65rem;text-align:right}}
th:first-child,td:first-child{{text-align:left}}.note{{font-size:.92rem;color:#444}}</style></head><body>
<h1>Alternative measures of unemployment</h1>
<p>IPUMS CPS basic monthly, {data.index.min():%B %Y} to {last_date:%B %Y}</p>
<img src="data:image/png;base64,{chart_b64}" alt="U-3 and U-1 rates, with LFPR in a separate panel">
<h2>Selected months</h2>{table_html}<h2>Interpretation</h2><p>{answer}</p>
<h2>Methods</h2><p class="note">Monthly estimates use WTFINL person weights. U-1 is unemployed for 15 or more weeks
as a percent of the labor force. LFPR is the labor force as a percent of the population age 16 and older.
The series runs continuously from January 2015 through {last_date:%B %Y}. Gray shading marks March through May 2020.
Source: IPUMS CPS basic monthly extract.</p></body></html>"""
(OUT / "report.html").write_text(html, encoding="utf-8")

from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as PdfImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

styles = getSampleStyleSheet()
story = [Paragraph("Alternative measures of unemployment", styles["Title"]),
         Paragraph(f"IPUMS CPS basic monthly, {data.index.min():%B %Y} to {last_date:%B %Y}", styles["Normal"]),
         Spacer(1, 7), PdfImage(str(OUT / "slack_chart.png"), width=7.1*inch, height=4.96*inch),
         Paragraph("Selected months", styles["Heading2"])]
pdf_rows = [["Period", "U-3", "U-1", "LFPR"]] + [
    [name] + [f"{row[c]:.2f}%" for c in required[1:]] for name, row in periods]
tbl = Table(pdf_rows, repeatRows=1, colWidths=[2.05*inch, 1.1*inch, 1.1*inch, 1.1*inch])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), rl_colors.HexColor("#e8eef4")),
    ("GRID", (0,0), (-1,-1), .4, rl_colors.grey),
    ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ("FONTSIZE", (0,0), (-1,-1), 9), ("PADDING", (0,0), (-1,-1), 4),
]))
method = (f"Monthly estimates use WTFINL person weights. U-1 is unemployed 15+ weeks as a share of the labor force; "
          f"LFPR is the labor force divided by the population age 16 and older. The continuous monthly series runs "
          f"from January 2015 through {last_date:%B %Y}. Gray shading marks March-May 2020. Source: IPUMS CPS "
          "basic monthly extract.")
story.extend([tbl, Paragraph("Interpretation", styles["Heading2"]), Paragraph(answer, styles["BodyText"]),
              Paragraph("Methods", styles["Heading2"]), Paragraph(method, styles["BodyText"])])
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=letter,
                  rightMargin=.7*inch, leftMargin=.7*inch,
                  topMargin=.45*inch, bottomMargin=.45*inch).build(story)
print(f"Rebuilt simplified deliverables from {RESULTS}; no microdata read.")
print(table.to_string())
