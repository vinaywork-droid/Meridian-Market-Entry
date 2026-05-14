"""
generate_raw_data_v2.py
-----------------------
Simulates raw data as it would arrive from 7 real client-side sources.
Formats: JSON, Excel (multi-sheet), CSV (clean and report-style), plain text.

Sources:
  1. market_research/city_indicators.json     — macro/demographic data (API export)
  2. distribution/retail_census.xlsx          — 4-sheet Excel from distribution partner
  3. nielsen/fmcg_report.xlsx                 — 2-sheet Nielsen FMCG data
  4. competitor/competitor_intelligence.csv   — quarterly competitor tracking
  5. logistics/vendor_report.csv              — messy report-style CSV from Blue Dart
  6. erp/[city]_sales.csv                     — SKU-level monthly sales (3 reference markets)
  7. internal/strategy_brief.txt              — internal strategy context note

Target cities for entry analysis: Nashik, Nagpur, Mysuru
Reference/benchmark markets: Mumbai, Pune, Aurangabad

Data quality issues are intentional — they mirror how data actually arrives.
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, 'data', 'raw')

DIRS = [
    'market_research', 'distribution', 'nielsen',
    'competitor', 'logistics', 'erp', 'internal'
]
for d in DIRS:
    os.makedirs(os.path.join(RAW_DIR, d), exist_ok=True)

# 18 months: Jan 2023 – Jun 2024
MONTHS = pd.date_range('2023-01-01', '2024-06-01', freq='MS')
MONTH_LABELS = [m.strftime('%b-%Y') for m in MONTHS]   # 'Jan-2023'
QUARTERS = ['Q1-2023','Q2-2023','Q3-2023','Q4-2023','Q1-2024','Q2-2024']

CITIES     = ['Nashik', 'Nagpur', 'Mysuru']
REF_MKTS   = ['Mumbai', 'Pune', 'Aurangabad']

# 15 SKUs across 5 categories
SKUS = [
    {'code':'PC001','name':'Meridian Shampoo 200ml',        'category':'Personal Care',    'mrp':180,'margin':0.28},
    {'code':'PC002','name':'Meridian Conditioner 150ml',    'category':'Personal Care',    'mrp':210,'margin':0.31},
    {'code':'PC003','name':'Meridian Face Wash 100g',       'category':'Personal Care',    'mrp':150,'margin':0.35},
    {'code':'PC004','name':'Meridian Body Lotion 250ml',    'category':'Personal Care',    'mrp':240,'margin':0.29},
    {'code':'HC001','name':'Meridian Dish Wash 500ml',      'category':'Home Care',        'mrp':90, 'margin':0.22},
    {'code':'HC002','name':'Meridian Floor Cleaner 1L',     'category':'Home Care',        'mrp':120,'margin':0.24},
    {'code':'HC003','name':'Meridian Toilet Cleaner 500ml', 'category':'Home Care',        'mrp':85, 'margin':0.21},
    {'code':'FB001','name':'Meridian Instant Noodles 70g',  'category':'Food & Beverages', 'mrp':15, 'margin':0.18},
    {'code':'FB002','name':'Meridian Breakfast Cereal 400g','category':'Food & Beverages', 'mrp':280,'margin':0.32},
    {'code':'FB003','name':'Meridian Fruit Juice 1L',       'category':'Food & Beverages', 'mrp':110,'margin':0.27},
    {'code':'HH001','name':'Meridian Hand Sanitizer 100ml', 'category':'Health & Hygiene', 'mrp':75, 'margin':0.38},
    {'code':'HH002','name':'Meridian Antiseptic 250ml',     'category':'Health & Hygiene', 'mrp':130,'margin':0.33},
    {'code':'HH003','name':'Meridian ORS Sachets 10pk',     'category':'Health & Hygiene', 'mrp':60, 'margin':0.25},
    {'code':'PF001','name':'Meridian Biscuits 200g',        'category':'Packaged Foods',   'mrp':40, 'margin':0.20},
    {'code':'PF002','name':'Meridian Namkeen 150g',         'category':'Packaged Foods',   'mrp':30, 'margin':0.19},
]

# Monthly seasonality index (all categories base)
SEASONAL = {
    1:1.05, 2:0.95, 3:1.00, 4:1.10, 5:1.15, 6:0.95,
    7:0.90, 8:0.92, 9:1.02, 10:1.38, 11:1.25, 12:1.10
}

# Category-level seasonal adjustments ON TOP of base
CAT_SEASONAL = {
    'Food & Beverages': {4:1.20, 5:1.25, 6:1.15, 7:0.88, 8:0.90},
    'Health & Hygiene': {4:1.18, 5:1.22, 6:1.15, 7:1.12, 8:1.10},
    'Home Care':        {7:1.18, 8:1.15},
    'Personal Care':    {10:1.15, 11:1.10},
}

# Monthly growth trend (~8% YoY = ~0.64% per month)
def growth_factor(month_idx):
    return (1 + 0.0064) ** month_idx

def seasonal_factor(month_num, category):
    base = SEASONAL.get(month_num, 1.0)
    cat_adj = CAT_SEASONAL.get(category, {}).get(month_num, 1.0)
    return base * cat_adj

def add_noise(val, pct=0.06):
    """Add ±6% random noise to simulate natural variance."""
    return int(val * (1 + np.random.uniform(-pct, pct)))


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — JSON: Market Research Firm — city_indicators.json
# Issues: inconsistent field names across cities, one month missing for Mysuru,
#         nested structure, income distribution as separate nested object
# ══════════════════════════════════════════════════════════════════════════════
def generate_json():
    city_config = {
        'Nashik': {
            'state': 'Maharashtra',
            'tier': 'Tier 2',
            'city_pop_2023': 1487053,
            'district_pop': 6107000,
            'median_hh_income_inr': 342000,
            'urban_pct': 70.2,
            'literacy_pct': 87.8,
            'gdp_growth_pct': 8.2,
            'working_age_pct': 64.3,
            'sec_distribution': {'SEC_A': 0.08, 'SEC_B': 0.18, 'SEC_C': 0.38, 'SEC_D': 0.36},
            'indicators_key': 'monthly_macro_indicators',     # ← field name varies
            'ci_key': 'consumer_confidence_index',
            'baseline_ci': 108.4
        },
        'Nagpur': {
            'state': 'Maharashtra',
            'tier': 'Tier 2',
            'city_pop_2023': 2497777,
            'district_pop': 5109000,
            'median_hh_income_inr': 418000,
            'urban_pct': 75.4,
            'literacy_pct': 91.3,
            'gdp_growth_pct': 7.8,
            'working_age_pct': 66.1,
            'sec_distribution': {'SEC_A': 0.11, 'SEC_B': 0.22, 'SEC_C': 0.37, 'SEC_D': 0.30},
            'indicators_key': 'monthly_indicators',            # ← different key
            'ci_key': 'consumer_confidence_idx',               # ← different suffix
            'baseline_ci': 112.1
        },
        'Mysuru': {
            'state': 'Karnataka',
            'tier': 'Tier 2',
            'city_pop_2023': 1001910,
            'district_pop': 3107000,
            'median_hh_income_inr': 378000,
            'urban_pct': 68.1,
            'literacy_pct': 88.6,
            'gdp_growth_pct': 9.1,
            'working_age_pct': 63.7,
            'sec_distribution': {'SEC_A': 0.09, 'SEC_B': 0.19, 'SEC_C': 0.36, 'SEC_D': 0.36},
            'indicators_key': 'indicators_monthly',            # ← yet another variation
            'ci_key': 'consumer_confidence_index',
            'baseline_ci': 105.7
        }
    }

    output = {
        'report_metadata': {
            'source': 'Market Research International (MRI)',
            'report_id': 'MRI-IND-2024-Q2-047',
            'coverage_period': 'January 2023 – June 2024',
            'delivery_format': 'JSON API Export v2.3',
            'generated_at': '2024-07-01T09:42:11Z',
            'note': 'Data reflects city municipal boundaries. District figures sourced separately.'
        },
        'cities': {}
    }

    for city, cfg in city_config.items():
        monthly = []
        for i, m in enumerate(MONTHS):
            # Skip Feb 2024 for Mysuru — missing from source
            if city == 'Mysuru' and m.strftime('%Y-%m') == '2024-02':
                continue

            noise = np.random.uniform(-0.3, 0.8)
            monthly.append({
                'period': m.strftime('%Y-%m'),
                cfg['ci_key']: round(cfg['baseline_ci'] + i * 0.18 + noise, 1),
                'retail_inflation_pct': round(5.8 + np.random.uniform(-0.6, 0.6), 2),
                'fmcg_category_growth_pct': round(cfg['gdp_growth_pct'] + np.random.uniform(-1.2, 1.5), 2),
                'new_business_registrations': int(180 * (cfg['city_pop_2023'] / 1500000) + np.random.randint(-15, 25)),
            })

        output['cities'][city] = {
            'demographics': {
                'state': cfg['state'],
                'classification': cfg['tier'],
                'city_population_2023': cfg['city_pop_2023'],
                'district_population': cfg['district_pop'],
                'median_annual_hh_income_inr': cfg['median_hh_income_inr'],
                'urban_population_pct': cfg['urban_pct'],
                'literacy_rate_pct': cfg['literacy_pct'],
                'gdp_growth_rate_pct_fy2324': cfg['gdp_growth_pct'],
                'working_age_population_pct': cfg['working_age_pct'],
            },
            'income_distribution': {               # SEC = Socio-Economic Classification
                'description': 'Share of households by SEC bracket (NCCS 2023 methodology)',
                'brackets': cfg['sec_distribution'],
                'primary_target_segments': ['SEC_B', 'SEC_C'],
            },
            cfg['indicators_key']: monthly         # intentionally different key per city
        }

    path = os.path.join(RAW_DIR, 'market_research', 'city_indicators.json')
    with open(path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"✓ market_research/city_indicators.json  ({sum(len(output['cities'][c][list(output['cities'][c].keys())[-1]]) for c in CITIES)} monthly records)")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — EXCEL: Distribution Partner — retail_census.xlsx (4 sheets)
# Issues: Sheet 4 has no analytical value (contact info), area names
#         inconsistent across sheets, one city missing cold chain data
# ══════════════════════════════════════════════════════════════════════════════
def generate_distribution_excel():
    # ── Sheet 1: Store Census (area-level) ──
    areas = {
        'Nashik':  ['Nashik Road','Dwarka','Satpur MIDC','Cidco','Panchavati','Gangapur Road',
                    'Ambad','Indira Nagar','College Road','Malegaon Road'],
        'Nagpur':  ['Dharampeth','Sitabuldi','Itwari','Kamptee Road','Wardha Road','Hingna MIDC',
                    'Civil Lines','Sadar','Manish Nagar','Koradi Road'],
        'Mysuru':  ['Vijayanagar','Hebbal','Kuvempunagar','Rajivnagar','Mysuru Road',
                    'Saraswathipuram','JP Nagar','Chamundi Hills Area','Bogadi','N R Mohalla'],
    }
    area_rows = []
    pop_weights = {'Nashik': 148705, 'Nagpur': 249778, 'Mysuru': 100191}
    for city, area_list in areas.items():
        base_pop = pop_weights[city]
        for area in area_list:
            kiranas = int(np.random.randint(180, 520) * (base_pop / 200000))
            area_rows.append({
                'City': city,
                'Area_Name': area,
                'Est_Kirana_Stores': kiranas,
                'Modern_Trade_Outlets': np.random.randint(0, 4),
                'Avg_Monthly_Offtake_Cases': int(kiranas * np.random.uniform(12, 22)),
                'Active_Distributor_Coverage_%': round(np.random.uniform(48, 79), 1),
                'Last_Audit_Date': f"{np.random.choice(['Jan','Feb','Mar'])}-2024",
                'Area_Tier': np.random.choice(['Urban Core','Urban Periphery','Semi-Urban'], p=[0.4,0.4,0.2])
            })
    sheet1 = pd.DataFrame(area_rows)

    # ── Sheet 2: Monthly Channel Coverage ──
    channels = ['General Trade (Kirana)', 'Modern Trade', 'Wholesale / Cash & Carry']
    cov_rows = []
    base_coverage = {
        'Nashik':  {'General Trade (Kirana)':61, 'Modern Trade':72, 'Wholesale / Cash & Carry':85},
        'Nagpur':  {'General Trade (Kirana)':74, 'Modern Trade':81, 'Wholesale / Cash & Carry':91},
        'Mysuru':  {'General Trade (Kirana)':55, 'Modern Trade':64, 'Wholesale / Cash & Carry':78},
    }
    for city in CITIES:
        for ch in channels:
            base = base_coverage[city][ch]
            for i, m in enumerate(MONTHS):
                drift = i * 0.3 + np.random.uniform(-1.2, 1.5)
                cov_rows.append({
                    'City': city,
                    'Channel': ch,
                    'Month': m.strftime('%b-%Y'),
                    'Coverage_%': min(round(base + drift, 1), 99.0),
                    'Active_Outlets': int((base / 100) * (1000 if city == 'Nagpur' else 600) + np.random.randint(-30, 30)),
                    'Avg_Order_Frequency_per_month': round(np.random.uniform(2.1, 4.8), 1),
                })
    sheet2 = pd.DataFrame(cov_rows)

    # ── Sheet 3: Infrastructure ──
    sheet3 = pd.DataFrame({
        'City':                         ['Nashik', 'Nagpur', 'Mysuru'],
        'Primary_Warehouse_Type':       ['3rd Party (Shree Distributors)', 'Owned Facility (proposed)', '3rd Party (Karnataka Trade Co.)'],
        'Warehouse_Capacity_MT':        [450, 820, 310],
        'Cold_Storage_Available':       ['Yes', 'Yes', None],           # Mysuru missing
        'Cold_Storage_Capacity_MT':     [80, 150, None],                # Mysuru missing
        'Avg_Freight_Cost_per_MT_INR':  [2800, 5200, 7800],
        'Last_Mile_Index_out_of_10':    [7.2, 8.4, 6.1],
        'Stockout_Risk_Rating':         ['Medium', 'Low', 'High'],
        'Road_Connectivity':            ['NH3 – Good', 'NH44 – Excellent', 'NH275 – Good'],
        'Transit_Time_from_Mumbai_hrs': [4.5, 14.0, 22.0],
    })

    # ── Sheet 4: Partner Contacts (noise — no analytical value) ──
    sheet4 = pd.DataFrame({
        'Partner_Name':    ['Shree Distributors Nashik','Central India Dist. Pvt Ltd','Karnataka Trade Co.'],
        'Contact_Person':  ['Ramesh Patil','Vijay Deshmukh','Suresh Gowda'],
        'Mobile':          ['98XXXXXXXX', '97XXXXXXXX', '96XXXXXXXX'],
        'Email':           ['ramesh@shreedist.com','vijay@cidpl.in','suresh@ktco.co.in'],
        'Contract_Expiry': ['March 2026','December 2025','June 2025'],
        'Commission_%':    [4.2, 3.8, 4.5],
        'Last_Review_Meeting': ['12-Feb-2024','28-Jan-2024','05-Mar-2024'],
    })

    path = os.path.join(RAW_DIR, 'distribution', 'retail_census.xlsx')
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        sheet1.to_excel(writer, sheet_name='Store Census',          index=False)
        sheet2.to_excel(writer, sheet_name='Monthly Channel Cov.',  index=False)
        sheet3.to_excel(writer, sheet_name='Infrastructure',        index=False)
        sheet4.to_excel(writer, sheet_name='Partner Contacts',      index=False)
    print(f"✓ distribution/retail_census.xlsx  ({len(sheet1)+len(sheet2)+len(sheet3)+len(sheet4)} rows across 4 sheets)")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — EXCEL: Nielsen FMCG Report — fmcg_report.xlsx (2 sheets)
# Issues: Mysuru spend noted as weekly (not monthly like others),
#         Q4-2023 penetration data missing for Mysuru (older report batch),
#         category names slightly inconsistent between sheets
# ══════════════════════════════════════════════════════════════════════════════
def generate_nielsen_excel():
    CATEGORIES = ['Personal Care','Home Care','Food & Beverages','Health & Hygiene','Packaged Foods','Dairy & Bakery']

    # Monthly baseline HH spend (INR/month)
    base_spend = {
        'Nashik': {'Personal Care':680,'Home Care':420,'Food & Beverages':890,
                   'Health & Hygiene':310,'Packaged Foods':560,'Dairy & Bakery':340},
        'Nagpur': {'Personal Care':820,'Home Care':510,'Food & Beverages':1080,
                   'Health & Hygiene':390,'Packaged Foods':680,'Dairy & Bakery':410},
        'Mysuru': {'Personal Care':720,'Home Care':390,'Food & Beverages':950,
                   'Health & Hygiene':280,'Packaged Foods':490,'Dairy & Bakery':370},
    }
    yoy_growth = {
        'Personal Care':8.2,'Home Care':6.1,'Food & Beverages':9.4,
        'Health & Hygiene':11.2,'Packaged Foods':7.8,'Dairy & Bakery':5.9
    }

    # ── Sheet 1: Monthly HH Spend ──
    spend_rows = []
    for city in CITIES:
        for i, m in enumerate(MONTHS):
            for cat in CATEGORIES:
                base = base_spend[city][cat]
                growth = (1 + yoy_growth[cat] / 100 / 12) ** i
                s_factor = seasonal_factor(m.month, cat)
                spend = round(base * growth * s_factor + np.random.uniform(-18, 18), 0)

                # Mysuru data is per week (source issue)
                reported_spend = round(spend / 4.33, 0) if city == 'Mysuru' else spend
                period_note    = 'Weekly' if city == 'Mysuru' else 'Monthly'

                spend_rows.append({
                    'Market':               city,
                    'Period':               m.strftime('%b-%Y'),
                    'FMCG_Category':        cat,
                    'Avg_HH_Spend_INR':     int(reported_spend),
                    'Spend_Period':         period_note,           # KEY issue for ETL
                    'YoY_Growth_%':         round(yoy_growth[cat] + np.random.uniform(-1.5, 1.5), 2),
                    'Nielsen_Wave':         f"NIL-{'W' if city == 'Nashik' else 'C' if city == 'Nagpur' else 'S'}-{m.strftime('%Y')}-Q{(m.month-1)//3+1}",
                })
    sheet1 = pd.DataFrame(spend_rows)

    # ── Sheet 2: Quarterly Category Penetration ──
    # Category names slightly different here (as if from a different report module)
    cat_name_map = {
        'Personal Care':'Personal Care & Grooming',
        'Home Care':'Home & Fabric Care',
        'Food & Beverages':'Foods & Beverages',
        'Health & Hygiene':'Health, Hygiene & OTC',
        'Packaged Foods':'Packaged & Convenience Foods',
        'Dairy & Bakery':'Dairy, Bakery & Confectionery',
    }
    base_pen = {
        'Nashik': [78,91,96,67,73,88],
        'Nagpur': [82,94,97,71,76,91],
        'Mysuru': [75,89,95,63,69,85],
    }
    pen_rows = []
    for city in CITIES:
        for qi, qtr in enumerate(QUARTERS):
            for ci, cat in enumerate(CATEGORIES):
                # Skip Q4-2023 for Mysuru — missing from Nielsen South batch
                if city == 'Mysuru' and qtr == 'Q4-2023':
                    continue
                drift = qi * 0.4 + np.random.uniform(-0.8, 0.8)
                pen_rows.append({
                    'Market':                   city,
                    'Quarter':                  qtr,
                    'Category':                 cat_name_map[cat],    # different names from Sheet 1
                    'Penetration_%':            min(round(base_pen[city][ci] + drift, 1), 99.0),
                    'Switching_Index':          round(np.random.uniform(0.82, 1.18), 2),
                    'Brand_Loyalty_Score_10':   round(np.random.uniform(5.8, 8.4), 1),
                })
    sheet2 = pd.DataFrame(pen_rows)

    path = os.path.join(RAW_DIR, 'nielsen', 'fmcg_report.xlsx')
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        sheet1.to_excel(writer, sheet_name='Monthly HH Spend', index=False)
        sheet2.to_excel(writer, sheet_name='Category Penetration', index=False)
    print(f"✓ nielsen/fmcg_report.xlsx  ({len(sheet1)} spend rows | {len(sheet2)} penetration rows)")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 4 — CSV: Competitor Intelligence — competitor_intelligence.csv
# Issues: competitor names inconsistent, market shares sum > 100% in two cities,
#         smaller competitors missing for some quarters, 2022 data for Mysuru
# ══════════════════════════════════════════════════════════════════════════════
def generate_competitor_csv():
    competitors = {
        'Nashik': [
            ('Hindustan Unilever Ltd', 0.34, 82, 'Mass-Premium', 15),
            ('Dabur India',            0.15, 68, 'Mass',         12),
            ('ITC Limited',            0.12, 71, 'Mass-Premium', 10),
            ('Marico',                 0.08, 55, 'Premium',       8),
            ('Local/Regional Brands',  0.39, None,'Value',       None),  # sums > 100%
        ],
        'Nagpur': [
            ('HUL',                    0.37, 88, 'Mass-Premium', 20),   # HUL vs full name
            ('Procter & Gamble',       0.10, 61, 'Premium',       9),
            ('Dabur',                  0.14, 72, 'Mass',         14),
            ('ITC Ltd.',               0.11, 69, 'Mass',         11),
            ('Local Brands',           0.27, None,'Value',       None),
        ],
        'Mysuru': [
            ('Hindustan Unilever',     0.32, 76, 'Mass-Premium', 18),
            ('Marico Ltd',             0.13, 58, 'Premium',       7),
            ('Dabur India Ltd',        0.11, 64, 'Mass',         13),
            ('ITC',                    0.09, 61, 'Mass',         10),
            ('Local & Regional',       0.44, None,'Value',       None),  # sums > 100%
        ],
    }

    mkt_share_trend = {  # quarterly drift per competitor type
        'leader': -0.004, 'challenger': 0.002, 'local': 0.003
    }

    rows = []
    for city, comps in competitors.items():
        # Mysuru competitor data was from 2022 — older batch
        source_year = 2022 if city == 'Mysuru' else 2023

        for qi, qtr in enumerate(QUARTERS):
            for rank, (name, share, dist_reach, pricing, yrs) in enumerate(comps):
                # Smaller competitors (rank 3+) randomly missing some quarters
                if rank >= 3 and np.random.random() < 0.22:
                    continue
                # Local brands always missing distribution reach
                reach = None if 'Local' in name or 'Regional' in name else (
                    min(99, dist_reach + qi * 0.4 + np.random.uniform(-1.5, 1.5))
                )
                trend = mkt_share_trend['leader'] if rank == 0 else (
                    mkt_share_trend['local'] if 'Local' in name else mkt_share_trend['challenger']
                )
                adj_share = round(share + trend * qi + np.random.uniform(-0.005, 0.005), 3)

                rows.append({
                    'city':                     city,
                    'Quarter':                  qtr,
                    'Competitor':               name,
                    'Est_Market_Share':         f"{round(adj_share * 100, 1)}%",
                    'Distribution_Reach_%':     round(reach, 1) if reach else None,
                    'Price_Positioning':        pricing,
                    'Promotional_Activity':     np.random.choice(['High','Medium','Low'], p=[0.25,0.50,0.25]),
                    'Price_Index_vs_Category':  round(np.random.uniform(0.88, 1.18), 2),
                    'Years_in_Market':          yrs,
                    'Source_Year':              source_year,
                    'Data_Quality_Flag':        'STALE – 2022 batch' if source_year == 2022 else 'OK',
                })

    pd.DataFrame(rows).to_csv(os.path.join(RAW_DIR, 'competitor', 'competitor_intelligence.csv'), index=False)
    print(f"✓ competitor/competitor_intelligence.csv  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 5 — CSV: Logistics Vendor Report — vendor_report.csv
# Real-world issue: vendor sent a report-style file, not a clean table.
# Has title rows, blank lines, section headers, subtotals mixed into data.
# An analyst must manually identify the data rows — this is very common.
# ══════════════════════════════════════════════════════════════════════════════
def generate_logistics_csv():
    lines = [
        ['BLUE DART LOGISTICS & SUPPLY CHAIN SOLUTIONS'],
        ['Distribution Feasibility Assessment – Meridian Consumer Goods Pvt. Ltd.'],
        ['Report Reference: BD-MCG-2024-FEB-047'],
        ['Prepared by: Regional Ops Team (West & South India)'],
        ['Date: February 2024'],
        [],
        ['SECTION 1: ROUTE & CONNECTIVITY ANALYSIS'],
        [],
        ['City','Route','Distance_km','Primary_Highway','Road_Condition','Avg_Transit_hrs_from_Mumbai','Transit_Reliability_%'],
        ['Nashik','Mumbai - Nashik','180','NH3','Good – 4-lane','4.5','91'],
        ['Nagpur','Mumbai - Nagpur (via NH44)','872','NH44','Excellent – 6-lane expressway','14.0','95'],
        ['Mysuru','Pune - Mysuru (via Bengaluru)','1289','NH275','Good – minor bottlenecks near Bengaluru','22.0','84'],
        [],
        ['SECTION 2: COST STRUCTURE (per MT, INR)'],
        [],
        ['City','Primary_Freight_INR_per_MT','Secondary_Distribution_INR_per_MT','Total_Logistics_Cost_INR_per_MT','vs_Mumbai_Base_%'],
        ['Nashik','2800','620','3420','100%'],          # Mumbai = base (100%)
        ['Nagpur','5200','810','6010','176%'],
        ['Mysuru','7800','1140','8940','261%'],
        [],
        ['SUBTOTAL NOTE: Costs indexed against Mumbai hub baseline (₹3,420/MT = 100%)'],
        [],
        ['SECTION 3: WAREHOUSING'],
        [],
        ['City','Warehouse_Option','Available_Capacity_MT','Cost_per_sqft_monthly_INR','Cold_Chain','Min_Lease_months'],
        ['Nashik','3rd Party (Shree Dist.)','450','28','Available','12'],
        ['Nagpur','Owned facility viable','820+','22','Available','N/A – capex'],
        ['Mysuru','3rd Party only','310','32','NOT available in target zones','12'],
        [],
        ['SECTION 4: RISK ASSESSMENT'],
        [],
        ['City','Last_Mile_Index_10','Stockout_Risk','Primary_Risk_Factor','Recommended_Safety_Stock_weeks'],
        ['Nashik','7.2','Medium','Monsoon road disruption (NH3 Jul-Aug)','3'],
        ['Nagpur','8.4','Low','Minimal – central hub with multiple route options','2'],
        ['Mysuru','6.1','High','Distance from distribution hub + no cold chain','4'],
        [],
        ['END OF REPORT'],
        ['For queries contact: ops-west@bluedart.example.in'],
    ]

    path = os.path.join(RAW_DIR, 'logistics', 'vendor_report.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        import csv
        writer = csv.writer(f)
        writer.writerows(lines)
    print(f"✓ logistics/vendor_report.csv  (report-style, {len(lines)} lines including headers/blanks)")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 6 — CSV: ERP Sales Dump — [city]_sales.csv (3 files, one per ref market)
# Meridian's sales data from existing markets — used as benchmark for projections.
# Issues: stockout events (0 units, flagged), promotional periods inconsistently
#         marked, Aurangabad uses different date format, one SKU discontinued mid-period
# ══════════════════════════════════════════════════════════════════════════════
def generate_erp_csvs():
    # Mumbai baseline monthly units (established, mature market)
    mumbai_base = {
        'PC001':45000,'PC002':22000,'PC003':31000,'PC004':18000,
        'HC001':52000,'HC002':38000,'HC003':29000,
        'FB001':71000,'FB002':24000,'FB003':41000,
        'HH001':33000,'HH002':19000,'HH003':14000,
        'PF001':58000,'PF002':44000,
    }
    # Scale factors for other markets
    scale = {'Mumbai': 1.0, 'Pune': 0.32, 'Aurangabad': 0.14}

    # Stockout events: (market, sku_code, month_str)
    stockouts = {
        ('Aurangabad', 'HC001', '2023-07'),  # monsoon logistics
        ('Aurangabad', 'HC001', '2023-08'),
        ('Pune',       'FB003', '2023-05'),  # supply chain delay
        ('Mumbai',     'HH001', '2023-04'),  # demand surge post-COVID
    }

    # Promotional periods: (market, month_str) → all SKUs get promo flag
    promos = {
        ('Mumbai','2023-10'),('Pune','2023-10'),('Aurangabad','2023-10'),  # Diwali
        ('Mumbai','2023-11'),('Pune','2023-11'),('Aurangabad','2023-11'),
        ('Mumbai','2024-01'),('Pune','2024-01'),                           # New Year PC promo
        ('Mumbai','2023-06'),('Pune','2023-06'),('Aurangabad','2023-06'),  # Summer sale
    }

    for market in REF_MKTS:
        rows = []
        for sku in SKUS:
            code = sku['code']
            base = mumbai_base[code] * scale[market]

            # FB002 (Breakfast Cereal) discontinued in Aurangabad after Sep 2023
            discontinued_after = '2023-09' if (market == 'Aurangabad' and code == 'FB002') else None

            for i, m in enumerate(MONTHS):
                month_str = m.strftime('%Y-%m')

                if discontinued_after and month_str > discontinued_after:
                    continue  # SKU discontinued — no rows

                units = add_noise(base * growth_factor(i) * seasonal_factor(m.month, sku['category']))
                is_stockout = (market, code, month_str) in stockouts
                is_promo = (market, month_str) in promos

                if is_stockout:
                    units = 0

                # Aurangabad uses DD/MM/YYYY — different from others
                date_fmt = m.strftime('%d/%m/%Y') if market == 'Aurangabad' else m.strftime('%Y-%m-%d')

                rows.append({
                    'Market':              market,
                    'Date':                date_fmt,
                    'SKU_Code':            code,
                    'SKU_Name':            sku['name'],
                    'Category':            sku['category'],
                    'Units_Sold':          units,
                    'MRP_INR':             sku['mrp'],
                    'Gross_Revenue_INR':   units * sku['mrp'],
                    'Margin_%':            round(sku['margin'] * 100, 1),
                    'Stockout_Flag':       'Y' if is_stockout else 'N',
                    'Promo_Period':        'Y' if is_promo else 'N',
                    'Promo_Type':          ('Diwali' if m.month in [10,11] else
                                           'NewYear-PC' if m.month == 1 else
                                           'Summer' if m.month == 6 else '') if is_promo else '',
                })

        fname = f"{market.lower().replace(' ','_')}_sales.csv"
        pd.DataFrame(rows).to_csv(os.path.join(RAW_DIR, 'erp', fname), index=False)
        print(f"✓ erp/{fname}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 7 — TXT: Internal Strategy Brief — strategy_brief.txt
# ══════════════════════════════════════════════════════════════════════════════
def generate_strategy_brief():
    content = """
MERIDIAN CONSUMER GOODS PVT. LTD.
INTERNAL STRATEGY BRIEF — FY2024-25 MARKET EXPANSION
CONFIDENTIAL — FOR INTERNAL USE ONLY
Prepared by: Corporate Strategy Team
Version: 2.1 | Date: April 2024

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPANY BACKGROUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Meridian Consumer Goods Pvt. Ltd. is a mid-market FMCG company established in 2009,
headquartered in Pune, Maharashtra. The company operates across five product categories:
Personal Care, Home Care, Food & Beverages, Health & Hygiene, and Packaged Foods.

FY2023-24 consolidated revenue: ₹187 crore (estimated).
Current distribution: Mumbai (primary), Pune (secondary), Aurangabad (pilot Tier-2).
Total SKU portfolio: 47 active SKUs. This engagement covers 15 priority SKUs.
Manufacturing: Two plants — Chakan (Pune) and Bhiwandi (Mumbai).
Brand positioning: Mass-to-mid-premium. Core customer: SEC B and C households.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXPANSION RATIONALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mumbai and Pune markets are approaching saturation for Meridian's core categories.
Distribution coverage in both cities exceeds 80%. Incremental growth requires
disproportionate marketing spend. The Board has approved one new city entry in
FY2024-25 with a capital allocation of ₹8-12 crore for Year 1 market development.

The expansion thesis: Tier-2 cities in Maharashtra and Karnataka are showing
accelerated FMCG growth driven by rising disposable incomes, modern trade
penetration, and digital media exposure. Meridian's Aurangabad pilot (FY2022-23)
achieved breakeven in Month 14 — ahead of the 18-month target.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANDIDATE CITIES — CONTEXT & CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NASHIK
Strategic fit: High. Proximity to Pune plant (~210 km) means low logistics cost
and ability to service with existing fleet. NH3 connectivity is reliable year-round
except minor monsoon disruptions (July-August). Growing industrial corridor (Satpur
and Ambad MIDC) is expanding the salaried workforce — Meridian's core demographic.
Regulatory: Standard Maharashtra trade license regime. No significant local body tax
complexity. APMC market at Malegaon Road is the primary wholesale entry point.
Risk: HUL and local brands are entrenched. Kirana coverage by competitors exceeds 70%.
Meridian would need 12-18 months to build meaningful distribution depth.

NAGPUR
Strategic fit: Medium-High. Largest of the three candidate cities. Serves as a
natural distribution hub for central India (Zero Mile City). Entry here opens
potential for future expansion into Vidarbha region (Amravati, Akola).
Logistics advantage: NH44 is India's longest national highway — Excellent condition.
Nagpur has an existing cold chain ecosystem (APMC cold storage, private facilities).
Regulatory: Maharashtra regime. MIDC industrial zones (Hingna, Butibori) have active
trade associations — relationship-building important for rapid retail penetration.
Financial consideration: Higher freight cost (₹5,200/MT vs ₹2,800 for Nashik) and
larger market requires proportionally higher Year-1 investment. Board may require
revised capex approval if Nagpur is selected.
Risk: P&G has recently increased promotional activity in the market (Q3-2023 onward).
HUL distribution reach is near 90%. Market entry without significant below-the-line
(BTL) investment will be slow.

MYSURU
Strategic fit: Medium. Only Karnataka candidate — entry would establish a South India
beachhead ahead of planned Bengaluru evaluation in FY2025-26. Mysuru's literacy rate
and consumer sophistication index favour Meridian's Health & Hygiene range.
Logistics concern: Distance from both manufacturing plants (1,200+ km) is a material
risk. No cold chain availability in target retail zones limits Personal Care SKU
rollout. Stockout risk rated HIGH by Blue Dart assessment.
Regulatory: Karnataka FMCG market has slightly more complex trade license requirements
than Maharashtra. Local body tax (LBT) was abolished in Karnataka in 2017 but
octroi-equivalent levies apply in some municipal zones — legal review required.
Language: Kannada-speaking market requires adapted packaging and in-store materials.
Estimated incremental cost: ₹30-45 lakh for packaging localisation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUDGET & DECISION TIMELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Available capex for Year-1 market entry: ₹8-12 crore.
Decision deadline: Board meeting scheduled for September 2024.
Analysis commissioned: External consulting engagement (this project).
Expected deliverable: City recommendation with financial model and risk assessment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERNAL CONSTRAINTS (NOT FOR CLIENT DISTRIBUTION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Sales team capacity: Max 8 additional field representatives can be onboarded in
  Year 1 without HR restructuring.
- Brand Marketing has earmarked ₹1.8 crore for launch BTL activity regardless of city.
- CFO preference is Nashik (logistics cost) but MD preference is Nagpur (scale).
  Recommendation should be evidence-driven, not consensus-driven.
- Aurangabad breakeven data is the most credible internal benchmark available.
  Use it as the primary projection reference.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF BRIEF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    path = os.path.join(RAW_DIR, 'internal', 'strategy_brief.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"✓ internal/strategy_brief.txt")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 62)
    print("MERIDIAN MARKET ENTRY — RAW DATA GENERATION v2")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    generate_json()
    generate_distribution_excel()
    generate_nielsen_excel()
    generate_competitor_csv()
    generate_logistics_csv()
    generate_erp_csvs()
    generate_strategy_brief()

    print()
    print("=" * 62)
    print("All source files generated in data/raw/")
    print("7 sources | 4 formats | realistic data quality issues")
    print("Next: delete old etl.py and write it fresh")
    print("=" * 62)
