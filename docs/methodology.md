# Methodology Note — Meridian Market Entry Analysis

## Purpose

This document explains the assumptions, frameworks, and reasoning behind 
this market entry analysis. It is intended for anyone evaluating the 
credibility and limitations of the recommendation.

## 1. Engagement Context

Meridian Consumer Goods Pvt. Ltd., a mid-market FMCG company based in Pune, 
commissioned this analysis to decide between three Tier 2 city candidates — 
Nashik, Nagpur, and Mysuru — for Year 1 market expansion. Available capex: 
₹8-12 crore. Full context is documented in the internal strategy brief 
(data/raw/internal/strategy_brief.txt).

## 2. Data Sources and Limitations

Data was simulated across 7 sources and 4 formats to replicate the data 
quality challenges of a real consulting engagement:

- Market research indicators (JSON) — Mysuru missing February 2024 data
- Distribution partner data (Excel, 4 sheets) — Partner Contacts sheet 
  excluded as non-analytical
- Nielsen FMCG report (Excel, 2 sheets) — Mysuru spend reported weekly, 
  converted to monthly (×4.33)
- Competitor intelligence (CSV) — market shares normalised to sum to 100% 
  per city per quarter; Mysuru data from 2022 (stale, flagged)
- Logistics vendor report (CSV, report-style) — parsed manually due to 
  non-tabular structure
- ERP sales data (CSV, 3 files) — Aurangabad used as primary revenue 
  benchmark due to comparable Tier 2 Maharashtra profile

All data cleaning logic and rationale is documented inline in scripts/etl.py.

## 3. Scoring Model — Pillar Weights

Four pillars were defined based on Meridian's specific situation 
(budget-constrained, existing Maharashtra presence, mass-to-mid-premium 
positioning):

| Pillar | Weight | Rationale |
|---|---|---|
| Market Attractiveness | 25% | Sets minimum viable market threshold |
| Competitive Landscape | 25% | Budget constraint makes competitive cost critical |
| Operational Feasibility | 30% | Logistics directly impacts breakeven timeline |
| Strategic Fit | 20% | Lower weight — all 3 cities pre-screened by client |

**Sensitivity analysis** was conducted by increasing Operational Feasibility 
to 40%, reflecting the CFO's cost-focused perspective noted in the strategy 
brief. Nagpur remained top-ranked under this scenario, strengthening 
confidence in the recommendation.

## 4. Financial Model Assumptions

**TAM Calculation:** City Households × SEC B+C Share × Avg Monthly FMCG 
Spend × 12. Average household size assumed at 4.2 (India national average).

**Revenue Projection:** Three scenarios (Conservative, Base, Optimistic) 
applied across 36 months, incorporating:
- Market share targets per scenario (3%/5%/7% in Year 1)
- Ramp factor — distribution build-up assumed at 65% capacity Month 1-6, 
  88% Month 7-12, full capacity Year 2 onwards
- Seasonal multipliers derived from EDA — October peak at 1.38× baseline 
  (Diwali), May at 1.15× (summer)

**Cost Structure:** Includes logistics (freight + warehousing), sales force 
(4-8 reps, ramping over 6 months), BTL marketing (front-loaded 2× in launch 
months), and fixed overheads.

**Capital Expenditure:** Allocated per city based on relative market size 
and city-specific factors — Nashik ₹8cr (lowest, proximity advantage), 
Nagpur ₹12cr (largest market, highest competitive intensity), Mysuru ₹11cr 
(includes Kannada packaging localisation estimate).

**Limitation:** Capex figures are estimates based on the strategy brief's 
budget range, not vendor-quoted figures. In a real engagement these would 
be validated with Meridian's finance team before finalising.

## 5. Risk Assessment Framework

Risks scored on Likelihood (1-5) × Impact (1-5) = Risk Score (max 25). 
Risk Level: High ≥15, Medium 8-14, Low <8.

Eight risks identified across Competitive, Operational, Financial, Market, 
Regulatory, People, and Macroeconomic categories. Top risk — competitive 
retaliation from HUL/P&G (Score 20) — informed the recommended phased 
entry strategy targeting underpenetrated areas first.

## 6. AI Report Generation

Structured analytical outputs (scorecard, financial projections, risk 
register) were passed to Groq API (Llama 3.3 70B) to generate the final 
narrative report. Raw data was pre-aggregated before API submission to 
ensure accuracy and avoid hallucination risk — the model synthesises 
pre-calculated findings rather than performing calculations itself.

## 7. Key Limitations

- All underlying data is simulated, not real Meridian or market data
- Capex and cost assumptions are estimates pending client/vendor validation
- Competitor intelligence reflects 18 months of data — does not capture 
  potential future competitive responses beyond what's modelled in the 
  risk assessment
- Financial model assumes linear ramp-up; real market entry often shows 
  non-linear adoption curves

## 8. Methodology Validation

The recommendation was cross-checked across three independent analytical 
layers — EDA (qualitative), Scoring Model (systematic weighted evaluation), 
and Financial Model (quantitative projection). EDA initially favoured 
Nashik based on competitive intensity concerns; the Scoring Model and 
Financial Model both independently confirmed Nagpur as the optimal choice, 
strengthening confidence that the recommendation is not an artefact of any 
single methodology.