"""
financial_model.py
------------------
Stage 6: Financial Model

Builds bottom-up revenue projections, cost structure, and breakeven
analysis for each candidate city across three scenarios.

Components:
  1. TAM Calculation
  2. Revenue Projection (Month 1-36)
  3. Cost Structure
  4. Breakeven Analysis

Scenarios: Conservative, Base, Optimistic

Author: Vinay Wakadkar
Project: Meridian Consumer Goods — Market Entry Analysis
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'database', 'meridian.db')
OUT_DIR  = os.path.join(BASE_DIR, 'outputs', 'reports')
os.makedirs(OUT_DIR, exist_ok=True)

# ── Database connection ────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)

# ── Scenario assumptions ───────────────────────────────────────
SCENARIOS = {
    'Conservative': {
        'market_share_yr1':  0.03,
        'market_share_yr2':  0.055,
        'market_share_yr3':  0.08,
        'ramp_factor_m1_m6': 0.55,
        'ramp_factor_m7_m12':0.80,
    },
    'Base': {
        'market_share_yr1':  0.05,
        'market_share_yr2':  0.08,
        'market_share_yr3':  0.12,
        'ramp_factor_m1_m6': 0.65,
        'ramp_factor_m7_m12':0.88,
    },
    'Optimistic': {
        'market_share_yr1':  0.07,
        'market_share_yr2':  0.11,
        'market_share_yr3':  0.15,
        'ramp_factor_m1_m6': 0.75,
        'ramp_factor_m7_m12':0.95,
    }
}

# ── Seasonal multipliers (from EDA) ───────────────────────────
SEASONAL = {
    1:1.05, 2:0.95, 3:1.00, 4:1.10, 5:1.15, 6:0.95,
    7:0.90, 8:0.92, 9:1.02, 10:1.38, 11:1.25, 12:1.10
}

# ── Initial capital expenditure per city ───────────────────────
CAPEX = {
    'Nashik': 80000000,
    'Nagpur': 120000000,
    'Mysuru': 110000000,
}


CITIES = ['Nashik', 'Nagpur', 'Mysuru']

def calculate_tam(conn):
    """
    Calculates Total Addressable Market for each city.
    
    TAM = City Households × SEC B+C Share × Monthly FMCG Spend × 12
    
    City Households = City Population / Average Household Size (4.2 for India)
    """
    demographics = pd.read_sql("SELECT * FROM demographics", conn)
    sec = pd.read_sql("SELECT * FROM sec_distribution", conn)
    spend = pd.read_sql("SELECT * FROM consumer_spend", conn)

    # ── Households per city ────────────────────────────────────
    AVG_HH_SIZE = 4.2  # Indian average household size
    demographics['total_households'] = (
        demographics['city_population'] / AVG_HH_SIZE
    ).astype(int)

    # ── SEC B+C share ──────────────────────────────────────────
    target_sec = sec[sec['bracket'].isin(['SEC_B', 'SEC_C'])]
    sec_share = target_sec.groupby('city')['share'].sum().reset_index()
    sec_share.columns = ['city', 'sec_bc_share']

    # ── Average monthly FMCG spend ─────────────────────────────
    avg_spend = spend.groupby('city')['avg_hh_spend_monthly_inr'].mean().reset_index()
    avg_spend.columns = ['city', 'avg_monthly_spend_inr']

    # ── TAM calculation ────────────────────────────────────────
    tam = demographics[['city', 'city_population', 'total_households']]\
        .merge(sec_share, on='city')\
        .merge(avg_spend, on='city')

    tam['target_households'] = (
        tam['total_households'] * tam['sec_bc_share']
    ).astype(int)

    tam['annual_tam_inr'] = (
        tam['target_households'] * tam['avg_monthly_spend_inr'] * 12
    ).astype(int)

    tam['annual_tam_crore'] = (tam['annual_tam_inr'] / 1e7).round(2)

    print("=== TOTAL ADDRESSABLE MARKET ===")
    print(tam[['city', 'total_households', 'target_households',
               'avg_monthly_spend_inr', 'annual_tam_crore']].to_string(index=False))
    print("\n(TAM in ₹ crore — annual, SEC B+C households only)")

    return tam[['city', 'total_households', 'target_households',
                'avg_monthly_spend_inr', 'annual_tam_inr', 'annual_tam_crore']]

def project_revenue(tam, conn):
    """
    Projects monthly revenue for 36 months per city per scenario.
    
    Revenue = TAM × Market Share × Ramp Factor × Seasonal Multiplier
    """
    all_projections = []

    for _, city_row in tam.iterrows():
        city = city_row['city']
        annual_tam = city_row['annual_tam_inr']
        monthly_tam = annual_tam / 12

        for scenario_name, assumptions in SCENARIOS.items():
            for month in range(1, 37):
                # ── Determine year and market share ───────────
                if month <= 12:
                    year = 1
                    market_share = assumptions['market_share_yr1']
                elif month <= 24:
                    year = 2
                    market_share = assumptions['market_share_yr2']
                else:
                    year = 3
                    market_share = assumptions['market_share_yr3']

                # ── Ramp factor ────────────────────────────────
                if month <= 6:
                    ramp = assumptions['ramp_factor_m1_m6']
                elif month <= 12:
                    ramp = assumptions['ramp_factor_m7_m12']
                else:
                    ramp = 1.0  # Full capacity from Year 2

                # ── Seasonal multiplier ────────────────────────
                month_of_year = ((month - 1) % 12) + 1
                seasonal = SEASONAL[month_of_year]

                # ── Monthly revenue ────────────────────────────
                monthly_revenue = (
                    monthly_tam * market_share * ramp * seasonal
                )

                all_projections.append({
                    'city':           city,
                    'scenario':       scenario_name,
                    'month':          month,
                    'year':           year,
                    'market_share':   market_share,
                    'ramp_factor':    ramp,
                    'seasonal_mult':  seasonal,
                    'monthly_revenue_inr': monthly_revenue,
                    'monthly_revenue_lakh': monthly_revenue / 1e5,
                })

    projections = pd.DataFrame(all_projections)

    # ── Print Year 1 summary ───────────────────────────────────
    yr1 = projections[projections['year'] == 1]\
        .groupby(['city', 'scenario'])['monthly_revenue_inr']\
        .sum().reset_index()
    yr1['annual_revenue_crore'] = (yr1['monthly_revenue_inr'] / 1e7).round(2)
    yr1 = yr1.sort_values(['scenario', 'city'])

    print("\n=== YEAR 1 PROJECTED REVENUE BY CITY AND SCENARIO ===")
    print(yr1[['city', 'scenario', 'annual_revenue_crore']].to_string(index=False))

    return projections

def calculate_costs(conn):
    """
    Builds monthly cost structure for each city over 36 months.
    
    Cost components:
      - Logistics (freight + warehousing)
      - Sales force (field representatives)
      - Marketing & BTL (below the line)
      - Distribution margin (trade margin paid to distributors)
      - Fixed overheads
    """
    logistics = pd.read_sql("SELECT * FROM logistics", conn)
    logistics['Total_Logistics_Cost_INR_per_MT'] = pd.to_numeric(
        logistics['Total_Logistics_Cost_INR_per_MT'], errors='coerce')
    logistics['Cost_per_sqft_monthly_INR'] = pd.to_numeric(
        logistics['Cost_per_sqft_monthly_INR'], errors='coerce')

    # ── Cost assumptions ───────────────────────────────────────
    # Based on strategy brief and industry benchmarks
    COST_ASSUMPTIONS = {
        'warehouse_sqft':        2000,    # initial warehouse size
        'sales_reps':            8,       # max per strategy brief
        'salary_per_rep_monthly':35000,   # INR per month
        'btl_budget_annual':     18000000,# ₹1.8 crore per strategy brief
        'distributor_margin_pct':0.042,   # 4.2% of revenue
        'fixed_overhead_monthly':150000,  # office, admin, misc
        'avg_mt_per_month':      15,      # estimated monthly volume MT
    }

    all_costs = []

    for _, city_row in logistics.iterrows():
        city = city_row['city']
        freight_per_mt = city_row['Total_Logistics_Cost_INR_per_MT']
        warehouse_per_sqft = city_row['Cost_per_sqft_monthly_INR']

        for month in range(1, 37):
            # ── Logistics cost ─────────────────────────────────
            freight_cost = (
                COST_ASSUMPTIONS['avg_mt_per_month'] * freight_per_mt
            )
            warehouse_cost = (
                COST_ASSUMPTIONS['warehouse_sqft'] * warehouse_per_sqft
            )

            # ── Sales force — ramp up over first 6 months ─────
            if month <= 3:
                active_reps = 4
            elif month <= 6:
                active_reps = 6
            else:
                active_reps = COST_ASSUMPTIONS['sales_reps']

            salesforce_cost = (
                active_reps * COST_ASSUMPTIONS['salary_per_rep_monthly']
            )

            # ── BTL marketing — higher in launch months ────────
            if month <= 3:
                btl_multiplier = 2.0   # heavy launch spend
            elif month <= 6:
                btl_multiplier = 1.5
            else:
                btl_multiplier = 1.0

            btl_cost = (
                COST_ASSUMPTIONS['btl_budget_annual'] / 12
            ) * btl_multiplier

            # ── Fixed overhead ─────────────────────────────────
            fixed_cost = COST_ASSUMPTIONS['fixed_overhead_monthly']

            # ── Total monthly cost ─────────────────────────────
            total_cost = (
                freight_cost + warehouse_cost +
                salesforce_cost + btl_cost + fixed_cost
            )

            all_costs.append({
                'city':               city,
                'month':              month,
                'freight_cost':       freight_cost,
                'warehouse_cost':     warehouse_cost,
                'salesforce_cost':    salesforce_cost,
                'btl_cost':           btl_cost,
                'fixed_cost':         fixed_cost,
                'total_monthly_cost': total_cost,
            })

    costs = pd.DataFrame(all_costs)

    # ── Year 1 cost summary ────────────────────────────────────
    yr1_costs = costs[costs['month'] <= 12]\
        .groupby('city')['total_monthly_cost'].sum().reset_index()
    yr1_costs['annual_cost_crore'] = (yr1_costs['total_monthly_cost'] / 1e7).round(2)

    print("\n=== YEAR 1 TOTAL COST BY CITY ===")
    print(yr1_costs[['city', 'annual_cost_crore']].to_string(index=False))

    return costs

def calculate_breakeven(projections, costs):
    """
    Calculates cumulative revenue vs cumulative cost per city per scenario.
    Includes initial capex as starting deficit.
    Identifies the month when cumulative revenue exceeds cumulative cost + capex.
    """
    all_breakeven = []

    for city in CITIES:
        city_costs = costs[costs['city'] == city][['month', 'total_monthly_cost']].copy()

        for scenario in SCENARIOS.keys():
            city_proj = projections[
                (projections['city'] == city) &
                (projections['scenario'] == scenario)
            ][['month', 'monthly_revenue_inr']].copy()

            # ── Merge revenue and cost ─────────────────────────
            monthly = city_proj.merge(city_costs, on='month')

            # ── Cumulative calculations ────────────────────────
            monthly['cumulative_revenue'] = monthly['monthly_revenue_inr'].cumsum()
            monthly['cumulative_cost']    = monthly['total_monthly_cost'].cumsum()

            # ── Apply capex as starting deficit ────────────────
            monthly['cumulative_profit']  = (
                monthly['cumulative_revenue'] -
                monthly['cumulative_cost'] -
                CAPEX[city]
            )

            # ── Find breakeven month ───────────────────────────
            breakeven_months = monthly[monthly['cumulative_profit'] >= 0]
            if len(breakeven_months) > 0:
                breakeven_month = breakeven_months['month'].iloc[0]
            else:
                breakeven_month = None

            monthly['city']     = city
            monthly['scenario'] = scenario
            all_breakeven.append(monthly)

            print(f"  {city} | {scenario:12s} → "
                  f"Breakeven: Month {breakeven_month if breakeven_month else 'Beyond 36'}")

    breakeven_df = pd.concat(all_breakeven, ignore_index=True)
    return breakeven_df


def plot_breakeven(breakeven_df):
    """
    Plots cumulative revenue vs cumulative cost for each city
    across all three scenarios.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    scenario_colors = {
        'Conservative': '#d62728',
        'Base':         '#2ca02c',
        'Optimistic':   '#1f77b4'
    }

    for i, city in enumerate(CITIES):
        ax = axes[i]
        city_data = breakeven_df[breakeven_df['city'] == city]

        # Plot cost line once — same for all scenarios
        cost_data = city_data[city_data['scenario'] == 'Base']
        ax.plot(cost_data['month'], cost_data['cumulative_cost'] / 1e7,
                color='black', linewidth=2, linestyle='--', label='Cumulative Cost')

        # Plot revenue line per scenario
        for scenario, color in scenario_colors.items():
            scen_data = city_data[city_data['scenario'] == scenario]
            ax.plot(scen_data['month'], scen_data['cumulative_revenue'] / 1e7,
                    color=color, linewidth=2, label=scenario)

        ax.set_title(f'{city} — Breakeven Analysis', fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Cumulative INR (Crore)')
        ax.legend(fontsize=8)
        ax.axhline(y=0, color='grey', linestyle=':', linewidth=0.8)

    plt.suptitle('Cumulative Revenue vs Cost — All Cities & Scenarios',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'breakeven_analysis.png'),
                dpi=150, bbox_inches='tight')
    plt.show()
    print("\nChart saved to outputs/reports/breakeven_analysis.png")


# ── Main ───────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("MERIDIAN MARKET ENTRY — FINANCIAL MODEL")
    print("=" * 60)

    tam         = calculate_tam(conn)
    projections = project_revenue(tam, conn)
    costs       = calculate_costs(conn)

    print("\n=== BREAKEVEN ANALYSIS ===")
    breakeven_df = calculate_breakeven(projections, costs)

    plot_breakeven(breakeven_df)

    # ── Save projections ───────────────────────────────────────
    projections.to_csv(os.path.join(OUT_DIR, 'revenue_projections.csv'), index=False)
    costs.to_csv(os.path.join(OUT_DIR, 'cost_structure.csv'), index=False)
    breakeven_df.to_csv(os.path.join(OUT_DIR, 'breakeven_analysis.csv'), index=False)

    print("\n=== FILES SAVED ===")
    print("  outputs/reports/revenue_projections.csv")
    print("  outputs/reports/cost_structure.csv")
    print("  outputs/reports/breakeven_analysis.csv")
    print("  outputs/reports/breakeven_analysis.png")

    conn.close()
    print("\nFinancial model complete.")

