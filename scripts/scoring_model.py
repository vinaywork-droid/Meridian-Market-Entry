"""
scoring_model.py
----------------
Stage 5: Screening Scorecard

Scores each candidate city across four pillars using cleaned data
from the SQLite database. Produces a weighted composite score and
city ranking to inform the financial model and final recommendation.

Pillars and weights:
  Market Attractiveness         — 25%
  Competitive Landscape         — 25%
  Operational Feasibility       — 30%
  Strategic Fit                 — 20%

Author: Vinay Wakadkar
Project: Meridian Consumer Goods — Market Entry Analysis
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import os

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'database', 'meridian.db')
OUT_DIR  = os.path.join(BASE_DIR, 'outputs', 'reports')
os.makedirs(OUT_DIR, exist_ok=True)

# ── Weights ────────────────────────────────────────────────────
WEIGHTS = {
    'market_attractiveness':    0.25,
    'competitive_landscape':    0.25,
    'operational_feasibility':  0.30,
    'strategic_fit':            0.20,
}

CITIES = ['Nashik', 'Nagpur', 'Mysuru']

# ── Database connection ────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)

def score_market_attractiveness(conn):
    """
    Scores cities on market size and spending potential.
    Metrics:
      - City population
      - Median HH income
      - SEC B+C combined share
      - Average monthly HH spend
      - GDP growth rate
    """
    # Load data
    demographics = pd.read_sql("SELECT * FROM demographics", conn)
    sec = pd.read_sql("SELECT * FROM sec_distribution", conn)
    spend = pd.read_sql("SELECT * FROM consumer_spend", conn)

    # ── Metric 1: Population score ─────────────────────────────
    demo = demographics[['city', 'city_population', 
                          'median_hh_income_annual_inr',
                          'gdp_growth_rate_pct']].copy()

    # ── Metric 2: SEC B+C addressable market ──────────────────
    target_sec = sec[sec['bracket'].isin(['SEC_B', 'SEC_C'])]
    sec_score = target_sec.groupby('city')['share'].sum().reset_index()
    sec_score.columns = ['city', 'sec_bc_share']

    # ── Metric 3: Average monthly HH spend ────────────────────
    avg_spend = spend.groupby('city')['avg_hh_spend_monthly_inr'].mean().reset_index()
    avg_spend.columns = ['city', 'avg_monthly_spend']

    # ── Combine all metrics ────────────────────────────────────
    df = demo.merge(sec_score, on='city').merge(avg_spend, on='city')

    # ── Normalise each metric to 0-1 scale ────────────────────
    metrics = ['city_population', 'median_hh_income_annual_inr',
               'gdp_growth_rate_pct', 'sec_bc_share', 'avg_monthly_spend']

    for metric in metrics:
        min_val = df[metric].min()
        max_val = df[metric].max()
        df[f'{metric}_norm'] = (df[metric] - min_val) / (max_val - min_val)

    # ── Composite score — equal weight across metrics ──────────
    norm_cols = [f'{m}_norm' for m in metrics]
    df['market_attractiveness_score'] = df[norm_cols].mean(axis=1)

    print("=== MARKET ATTRACTIVENESS SCORES ===")
    print(df[['city'] + norm_cols + ['market_attractiveness_score']].to_string(index=False))

    return df[['city', 'market_attractiveness_score']]

def score_competitive_landscape(conn):
    """
    Scores cities on competitive intensity.
    Lower competition = higher score.
    Metrics:
      - HUL market share (inverted — lower is better)
      - Number of organised competitors
      - Local brand share (higher = more opportunity)
      - Average competitor distribution reach (inverted)
    """
    competitors = pd.read_sql("SELECT * FROM competitor_intelligence", conn)

    # Use most recent quarter per city
    latest = competitors.groupby('city')['quarter'].max().reset_index()
    latest.columns = ['city', 'latest_quarter']
    recent = competitors.merge(latest, on='city')
    recent = recent[recent['quarter'] == recent['latest_quarter']]

    # ── Metric 1: HUL market share ─────────────────────────────
    hul = recent[recent['competitor'] == 'Hindustan Unilever (HUL)'][['city', 'market_share_normalised']]
    hul.columns = ['city', 'hul_share']

    # ── Metric 2: Number of organised competitors ──────────────
    organised = recent[recent['competitor'] != 'Local & Regional Brands']
    comp_count = organised.groupby('city')['competitor'].count().reset_index()
    comp_count.columns = ['city', 'competitor_count']

    # ── Metric 3: Local brand share ────────────────────────────
    local = recent[recent['competitor'] == 'Local & Regional Brands'][['city', 'market_share_normalised']]
    local.columns = ['city', 'local_share']

    # ── Metric 4: Average distribution reach of competitors ────
    avg_reach = organised.groupby('city')['distribution_reach_pct'].mean().reset_index()
    avg_reach.columns = ['city', 'avg_competitor_reach']

    # ── Combine ────────────────────────────────────────────────
    df = hul.merge(comp_count, on='city').merge(local, on='city').merge(avg_reach, on='city')

    # ── Normalise ──────────────────────────────────────────────
    # HUL share and competitor count — invert (lower = better for Meridian)
    for metric in ['hul_share', 'competitor_count', 'avg_competitor_reach']:
        min_val = df[metric].min()
        max_val = df[metric].max()
        df[f'{metric}_norm'] = 1 - ((df[metric] - min_val) / (max_val - min_val))

    # Local brand share — higher is better (more opportunity)
    min_val = df['local_share'].min()
    max_val = df['local_share'].max()
    df['local_share_norm'] = (df['local_share'] - min_val) / (max_val - min_val)

    # ── Composite score ────────────────────────────────────────
    norm_cols = ['hul_share_norm', 'competitor_count_norm', 
                 'local_share_norm', 'avg_competitor_reach_norm']
    df['competitive_landscape_score'] = df[norm_cols].mean(axis=1)

    print("\n=== COMPETITIVE LANDSCAPE SCORES ===")
    print(df[['city'] + norm_cols + ['competitive_landscape_score']].to_string(index=False))

    return df[['city', 'competitive_landscape_score']]

def score_operational_feasibility(conn):
    """
    Scores cities on logistics cost and operational capability.
    Lower cost and higher capability = higher score.
    Metrics:
      - Total logistics cost per MT (inverted)
      - Warehouse cost per sqft (inverted)
      - Last mile index (higher is better)
      - Stockout risk (converted to numeric, inverted)
      - Cold chain availability (binary)
    """
    logistics = pd.read_sql("SELECT * FROM logistics", conn)

    # Convert numeric columns
    logistics['Total_Logistics_Cost_INR_per_MT'] = pd.to_numeric(
        logistics['Total_Logistics_Cost_INR_per_MT'], errors='coerce')
    logistics['Cost_per_sqft_monthly_INR'] = pd.to_numeric(
        logistics['Cost_per_sqft_monthly_INR'], errors='coerce')
    logistics['Last_Mile_Index_10'] = pd.to_numeric(
        logistics['Last_Mile_Index_10'], errors='coerce')

    # ── Convert stockout risk to numeric ──────────────────────
    risk_map = {'Low': 1, 'Medium': 2, 'High': 3}
    logistics['stockout_risk_numeric'] = logistics['Stockout_Risk'].map(risk_map)

    # ── Convert cold chain to binary ──────────────────────────
    logistics['cold_chain_binary'] = logistics['Cold_Chain'].apply(
        lambda x: 1 if str(x).strip().lower().startswith('available') else 0
    )

    df = logistics[['city', 'Total_Logistics_Cost_INR_per_MT',
                    'Cost_per_sqft_monthly_INR', 'Last_Mile_Index_10',
                    'stockout_risk_numeric', 'cold_chain_binary']].copy()

    # ── Normalise ──────────────────────────────────────────────
    # Invert — lower cost and lower risk = higher score
    for metric in ['Total_Logistics_Cost_INR_per_MT',
                   'Cost_per_sqft_monthly_INR',
                   'stockout_risk_numeric']:
        min_val = df[metric].min()
        max_val = df[metric].max()
        df[f'{metric}_norm'] = 1 - ((df[metric] - min_val) / (max_val - min_val))

    # Last mile index — higher is better, no inversion
    min_val = df['Last_Mile_Index_10'].min()
    max_val = df['Last_Mile_Index_10'].max()
    df['last_mile_norm'] = (df['Last_Mile_Index_10'] - min_val) / (max_val - min_val)

    # Cold chain — already binary 0 or 1
    df['cold_chain_norm'] = df['cold_chain_binary'].astype(float)

    # ── Composite score ────────────────────────────────────────
    norm_cols = ['Total_Logistics_Cost_INR_per_MT_norm',
                 'Cost_per_sqft_monthly_INR_norm',
                 'stockout_risk_numeric_norm',
                 'last_mile_norm',
                 'cold_chain_norm']
    df['operational_feasibility_score'] = df[norm_cols].mean(axis=1)

    print("\n=== OPERATIONAL FEASIBILITY SCORES ===")
    print(df[['city'] + norm_cols + ['operational_feasibility_score']].to_string(index=False))

    return df[['city', 'operational_feasibility_score']]

def score_strategic_fit(conn):
    """
    Scores cities on alignment with Meridian's strategic position.
    Metrics:
      - Distribution coverage pct (higher = easier market entry)
      - GDP growth rate (forward-looking market potential)
      - Urban population pct (aligns with Meridian's channel strategy)
      - Working age population pct (core consumer demographic)
    """
    demographics = pd.read_sql("SELECT * FROM demographics", conn)
    infrastructure = pd.read_sql("SELECT * FROM infrastructure", conn)
    channel = pd.read_sql("SELECT * FROM channel_coverage", conn)

    # ── Average distribution coverage across all channels ──────
    avg_coverage = channel.groupby('city')['Coverage_%'].mean().reset_index()
    avg_coverage.columns = ['city', 'avg_distribution_coverage']

    # ── Merge demographics ─────────────────────────────────────
    df = demographics[['city', 'gdp_growth_rate_pct',
                        'urban_population_pct',
                        'working_age_pop_pct']].merge(avg_coverage, on='city')

    # ── Normalise all metrics — higher is better ───────────────
    metrics = ['gdp_growth_rate_pct', 'urban_population_pct',
               'working_age_pop_pct', 'avg_distribution_coverage']

    for metric in metrics:
        min_val = df[metric].min()
        max_val = df[metric].max()
        df[f'{metric}_norm'] = (df[metric] - min_val) / (max_val - min_val)

    # ── Composite score ────────────────────────────────────────
    norm_cols = [f'{m}_norm' for m in metrics]
    df['strategic_fit_score'] = df[norm_cols].mean(axis=1)

    print("\n=== STRATEGIC FIT SCORES ===")
    print(df[['city'] + norm_cols + ['strategic_fit_score']].to_string(index=False))

    return df[['city', 'strategic_fit_score']]

def calculate_composite_score(conn):
    """
    Combines all four pillar scores using defined weights.
    Produces final city ranking with sensitivity analysis.
    """
    # ── Run all scoring functions ──────────────────────────────
    market      = score_market_attractiveness(conn)
    competitive = score_competitive_landscape(conn)
    operational = score_operational_feasibility(conn)
    strategic   = score_strategic_fit(conn)

    # ── Merge all scores ───────────────────────────────────────
    scores = market.merge(competitive, on='city')\
                   .merge(operational, on='city')\
                   .merge(strategic, on='city')

    # ── Apply weights ──────────────────────────────────────────
    scores['weighted_score'] = (
        scores['market_attractiveness_score']   * WEIGHTS['market_attractiveness'] +
        scores['competitive_landscape_score']   * WEIGHTS['competitive_landscape'] +
        scores['operational_feasibility_score'] * WEIGHTS['operational_feasibility'] +
        scores['strategic_fit_score']           * WEIGHTS['strategic_fit']
    )

    scores = scores.sort_values('weighted_score', ascending=False).reset_index(drop=True)
    scores['rank'] = scores.index + 1

    print("\n" + "=" * 60)
    print("FINAL WEIGHTED SCORECARD")
    print("=" * 60)
    print(scores[['rank', 'city',
                  'market_attractiveness_score',
                  'competitive_landscape_score',
                  'operational_feasibility_score',
                  'strategic_fit_score',
                  'weighted_score']].round(3).to_string(index=False))

    # ── Sensitivity analysis ───────────────────────────────────
    print("\n=== SENSITIVITY ANALYSIS ===")
    print("How ranking changes if operational feasibility weight increases to 40%")

    alt_weights = {
        'market_attractiveness':   0.20,
        'competitive_landscape':   0.20,
        'operational_feasibility': 0.40,
        'strategic_fit':           0.20,
    }

    scores['alt_weighted_score'] = (
        scores['market_attractiveness_score']   * alt_weights['market_attractiveness'] +
        scores['competitive_landscape_score']   * alt_weights['competitive_landscape'] +
        scores['operational_feasibility_score'] * alt_weights['operational_feasibility'] +
        scores['strategic_fit_score']           * alt_weights['strategic_fit']
    )

    alt_scores = scores.sort_values('alt_weighted_score', ascending=False).reset_index(drop=True)
    alt_scores['alt_rank'] = alt_scores.index + 1
    print(alt_scores[['city', 'weighted_score', 'alt_weighted_score', 
                       'alt_rank']].round(3).to_string(index=False))

    # ── Save scores to JSON for financial model ────────────────
    output = scores[['city', 'market_attractiveness_score',
                     'competitive_landscape_score',
                     'operational_feasibility_score',
                     'strategic_fit_score',
                     'weighted_score', 'rank']].to_dict(orient='records')

    out_path = os.path.join(OUT_DIR, 'scorecard.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nScorecard saved to: {out_path}")

    return scores


# ── Main ───────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("MERIDIAN MARKET ENTRY — SCORING MODEL")
    print("=" * 60)
    final_scores = calculate_composite_score(conn)
    conn.close()

