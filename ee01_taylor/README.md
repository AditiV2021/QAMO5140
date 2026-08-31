Empirical Exercise 1: The Taylor Rule
Context
In 2015, former Fed Chair Ben Bernanke responded to longstanding criticism from Stanford economist John Taylor, who argued that the Federal Reserve kept interest rates too low in the 2000s and thereby fueled the housing bubble. Taylor's critique rested on his famous "Taylor Rule" -- a simple formula that prescribes what the federal funds rate should be based on inflation and the output gap.

Bernanke countered that an updated version of the Taylor Rule -- one that uses core PCE inflation instead of the GDP deflator and places a larger weight on the output gap -- actually tracks Fed policy quite closely. In other words, Bernanke argued the Fed was following a rule, just a better-specified one.

In this exercise, you will replicate the core of Bernanke's analysis and then extend it to evaluate recent monetary policy under Kevin Warsh. Is the current federal funds rate where the Taylor Rule says it should be?

Data
All data are publicly available from the Federal Reserve Bank of St. Louis (FRED). Download CSVs directly from these links (or use the API):

Variable	FRED Series	Link
Federal Funds Rate	FEDFUNDS	https://fred.stlouisfed.org/series/FEDFUNDSLinks to an external site.
GDP Deflator	GDPDEF	https://fred.stlouisfed.org/series/GDPDEFLinks to an external site.
Core PCE Deflator	PCEPILFE	https://fred.stlouisfed.org/series/PCEPILFELinks to an external site.
Potential Nominal GDP	NGDPPOT	https://fred.stlouisfed.org/series/NGDPPOTLinks to an external site.
Nominal GDP	GDP	https://fred.stlouisfed.org/series/GDPLinks to an external site.
You will need to align these series to a common quarterly frequency. Download each CSV and merge them by date in the tool of your choice. Note that NGDPPOT is a projection and runs years into the future, while GDP stops at the last published quarter -- check the end of your merged data before you plot it.

Reading
Ben Bernanke, "The Taylor Rule: A Benchmark for Monetary Policy?" (2015), Brookings Institution. https://www.brookings.edu/articles/the-taylor-rule-a-benchmark-for-monetary-policy/Links to an external site.

Read this before starting the exercise. Pay particular attention to the two versions of the rule Bernanke discusses.

Questions
Construct the output gap. Using Nominal GDP and Potential Nominal GDP, compute the output gap as:
Output Gap = 100 * (GDP - NGDPPOT) / NGDPPOT

This is a percent of potential GDP: the 2009Q2 value should be about -5, not -0.05. Report the output gap for the most recent quarter available and for 2009Q2 (the trough of the Great Recession), and check both against the numbers you computed by hand in class. What does a negative output gap mean economically?

Compute two versions of the Taylor Rule. Calculate the prescribed federal funds rate under:

The original Taylor Rule (1993): r = Inflation + 0.5 * Output Gap + 0.5 * (Inflation - 2) + 2, where Inflation is the year-over-year percent change in the GDP Deflator.

Bernanke's modified rule: r = Inflation + 1.0 * Output Gap + 0.5 * (Inflation - 2) + 2, where Inflation is the year-over-year percent change in the Core PCE Deflator.
Report both prescribed rates for the most recent quarter. How do they differ, and why? Note that the two rules differ in two ways -- the inflation measure and the weight on the output gap. Your 2021Q4 value for the modified rule should be close to the number you computed by hand in class; if it is not, debug before going further.

Create a time-series chart. Plot the actual Federal Funds Rate alongside Bernanke's modified Taylor Rule from 1993Q1 to the most recent quarter. The chart must pass the five-element checklist from class: a title that states the point, a y-axis label with units, a legend naming each series, a source note, and readable dates. In a few sentences, describe the key periods where the actual rate diverges from the rule.

Evaluate current monetary policy. Based on your chart and the most recent data: Is the current Federal Funds Rate at the right level according to the Taylor Rule? What does the rule suggest the Fed should do next? In 3-5 sentences, discuss whether you think the rule provides good guidance in the current environment.

Working in Codex / Claude Code
Complete this exercise in Codex or Claude Code, with your analysis written in Python or Stata.

Set the project up first. Make one folder, QAMO5140/ee01_taylor/, with data/ (raw downloads, never edited), code/, and output/. Keep a README.md saying what the goal or question is, where the data came from, and how to rerun. Your script must run end-to-end, from raw download to final chart, in one go.

Start practicing good habits, and include notes on them in your submission (a few sentences total):

Before you run: write down what you expect -- the sign and rough magnitude of the key result, and one sanity check you plan to use.
Verify: run at least one check that the output is right (for example, compare a computed value against a published number).
What (if anything) you fixed: note where the AI's first attempt was wrong, incomplete, or mislabeled, and what you changed.
Economic intuition: in one or two sentences, describe what the analysis means and why. What is the story it tells, in plain English?
The AI writes the code fast; your job is to specify the analysis clearly, catch its mistakes, and make sure the economics is right. Every number you report must appear in your script's printed output -- a number the agent told you in conversation but never computed is not a result. Your written interpretations should be your own.


