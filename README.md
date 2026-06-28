# Meridian Consumer Goods — Market Entry Analysis

This project simulates a real consulting market entry engagement for a fictional 
FMCG company, Meridian Consumer Goods Pvt. Ltd. It identifies the optimal city for 
market expansion among three Tier 2 Indian cities by analysing demographics, 
competition, logistics, and financial viability — culminating in a data-backed 
recommendation with breakeven timelines, revenue projections, and risk assessment.

**Live Dashboard:** [Looker Studio](https://datastudio.google.com/reporting/dfe4bf6b-1a30-4442-8cfa-9f85b0448c76)

## Business Problem

Meridian Consumer Goods, a mid-market FMCG company based in Pune, has approved 
₹8-12 crore for Year 1 market expansion into one new Tier 2 city. This project 
evaluates three candidates — Nashik, Nagpur, and Mysuru — and delivers a 
recommendation backed by a complete analytical workflow.

## Workflow

This project follows a full analyst-to-consultant workflow:

1. **Raw Data Simulation** — 7 sources, 4 formats (JSON, Excel, CSV, text), 
   intentionally realistic data quality issues
2. **ETL Pipeline** — Python-based cleaning and normalisation into SQLite
3. **Database Verification** — confirmed table integrity before analysis
4. **Exploratory Data Analysis** — Jupyter notebook with full analyst commentary
5. **Screening Scorecard** — weighted four-pillar evaluation with sensitivity analysis
6. **Financial Model** — TAM, revenue projections (3 scenarios), cost structure, breakeven analysis
7. **Risk Assessment** — structured risk register with heat map visualisation
8. **AI Report Generation** — Groq API synthesises all outputs into a 
   consultant-style recommendation report
9. **Dashboard** — Looker Studio visualisation of key findings

## Repository Structure

meridian-market-entry/

├── data/

│   ├── raw/              # 7 source files across 4 formats

│   └── database/         # SQLite database (generated, not tracked)

├── notebooks/

│   └── 01_EDA.ipynb       # Exploratory analysis with commentary

├── scripts/

│   ├── generate_raw_data_v2.py

│   ├── etl.py

│   ├── scoring_model.py

│   ├── financial_model.py

│   ├── risk_assessment.py

│   └── report_generator.py

├── outputs/

│   └── reports/          # All generated outputs — CSVs, charts, final report

├── docs/

│   └── methodology.md    # Detailed methodology and assumptions

└── README.md

## Key Findings

**Recommended City: Nagpur**

- Highest weighted scorecard score (0.622) across four pillars
- Largest Total Addressable Market (₹314 crore annually)
- Base scenario Year 1 revenue: ₹12.84 crore
- Breakeven: Month 14 (Base case), consistent with Meridian's Aurangabad pilot precedent
- Primary risk: Competitive retaliation from HUL/P&G — mitigated through 
  phased distribution strategy targeting underpenetrated areas first

Full reasoning, alternative scenarios, and risk mitigation strategies are 
documented in [docs/methodology.md](docs/methodology.md) and the 
[final recommendation report](outputs/reports/market_entry_recommendation.txt).

## Tools & Technologies

- **Python** — pandas, numpy, matplotlib, seaborn
- **Jupyter Notebook** — exploratory analysis
- **SQLite** — data modelling
- **Groq API** — AI-powered report generation (LLM integration)
- **Looker Studio** — dashboard and visualisation
- **Git/GitHub** — version control

## Running This Project

```bash
# Clone the repository
git clone https://github.com/vinaywork-droid/Meridian-Market-Entry.git
cd meridian-market-entry

# Install dependencies
pip install pandas numpy matplotlib seaborn openpyxl groq

# Generate raw data
python scripts/generate_raw_data_v2.py

# Run ETL pipeline
python scripts/etl.py

# Run scoring model
python scripts/scoring_model.py

# Run financial model
python scripts/financial_model.py

# Run risk assessment
python scripts/risk_assessment.py

# Generate AI report (requires GROQ_API_KEY environment variable)
python scripts/report_generator.py
```

## Author

**Vinay Wakadkar**
[LinkedIn](https://www.linkedin.com/in/vinay-wakadkar-8069781a9/) | [GitHub](https://github.com/vinaywork-droid)

