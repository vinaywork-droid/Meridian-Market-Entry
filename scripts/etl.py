"""
etl.py
------
Stage 2: Extract, Transform, Load

Reads all 7 raw sources, handles every data quality issue identified
in the data audit, and loads clean normalised tables into SQLite.

Author: Vinay Wakadkar
Project: Meridian Consumer Goods — Market Entry Analysis
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import os
import logging
from datetime import datetime

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
DB_PATH = os.path.join(BASE_DIR, 'data', 'database', 'meridian.db')

# ── Standardisation maps ───────────────────────────────────────
CITY_MAP = {
    'nashik': 'Nashik',
    'nashik city': 'Nashik',
    'nagpur': 'Nagpur',
    'nagpur (city)': 'Nagpur',
    'mysuru': 'Mysuru',
    'mysore': 'Mysuru',
    'mysore city': 'Mysuru',
}

COMPETITOR_MAP = {
    'hindustan unilever ltd': 'Hindustan Unilever (HUL)',
    'hindustan unilever': 'Hindustan Unilever (HUL)',
    'hul': 'Hindustan Unilever (HUL)',
    'dabur india': 'Dabur India',
    'dabur': 'Dabur India',
    'dabur india ltd': 'Dabur India',
    'itc limited': 'ITC Limited',
    'itc ltd.': 'ITC Limited',
    'itc': 'ITC Limited',
    'marico': 'Marico',
    'marico ltd': 'Marico',
    'procter & gamble': 'Procter & Gamble (P&G)',
    'local/regional brands': 'Local & Regional Brands',
    'local brands': 'Local & Regional Brands',
    'local & regional': 'Local & Regional Brands',
}

CATEGORY_MAP = {
    'personal care': 'Personal Care',
    'personal care & grooming': 'Personal Care',
    'home care': 'Home Care',
    'home & fabric care': 'Home Care',
    'food & beverages': 'Food & Beverages',
    'foods & beverages': 'Food & Beverages',
    'food & bev': 'Food & Beverages',
    'health & hygiene': 'Health & Hygiene',
    'health, hygiene & otc': 'Health & Hygiene',
    'health/hygiene': 'Health & Hygiene',
    'packaged foods': 'Packaged Foods',
    'packaged & convenience foods': 'Packaged Foods',
    'dairy & bakery': 'Dairy & Bakery',
    'dairy, bakery & confectionery': 'Dairy & Bakery',
    'dairy': 'Dairy & Bakery',
}

# ── Helper functions ─────────────────────────────────────────
def normalise_city(val):
    if pd.isna(val):
        return None
    return CITY_MAP.get(str(val).strip().lower(), str(val).strip().title())

def normalise_category(val):
    if pd.isna(val):
        return None
    return CATEGORY_MAP.get(str(val).strip().lower(), str(val).strip().title())

def clean_json():
    log.info("Cleaning market research JSON...")
    
    path = os.path.join(RAW_DIR, 'market_research', 'city_indicators.json')
    with open(path, 'r') as f:
        raw = json.load(f)
    
    cities_data = raw['cities']
    
    # Monthly indicators key is different per city — find it dynamically
    # We know it contains a list, so we look for the key whose value is a list
    monthly_rows = []
    demo_rows = []
    sec_rows = []
    
    for city, content in cities_data.items():
        
        # ── Demographics ──
        demo = content['demographics']
        demo_rows.append({
            'city':                       normalise_city(city),
            'state':                      demo['state'],
            'city_population':            demo['city_population_2023'],
            'district_population':        demo['district_population'],
            'median_hh_income_annual_inr':demo['median_annual_hh_income_inr'],
            'urban_population_pct':       demo['urban_population_pct'],
            'literacy_rate_pct':          demo['literacy_rate_pct'],
            'gdp_growth_rate_pct':        demo['gdp_growth_rate_pct_fy2324'],
            'working_age_pop_pct':        demo['working_age_population_pct'],
        })
        
        # ── Income distribution (SEC brackets) ──
        sec = content['income_distribution']['brackets']
        for bracket, share in sec.items():
            sec_rows.append({
                'city':    normalise_city(city),
                'bracket': bracket,
                'share':   share,
            })
        
        # ── Monthly indicators ──
        # Find the key dynamically — it's the one whose value is a list
        monthly_key = next(k for k, v in content.items() if isinstance(v, list))
        
        for record in content[monthly_key]:
            monthly_rows.append({
                'city':                      normalise_city(city),
                'period':                    record['period'],
                'retail_inflation_pct':      record.get('retail_inflation_pct'),
                'fmcg_growth_pct':           record.get('fmcg_category_growth_pct'),
                'new_business_registrations':record.get('new_business_registrations'),
            })
    
    demographics = pd.DataFrame(demo_rows)
    sec_distribution = pd.DataFrame(sec_rows)
    monthly = pd.DataFrame(monthly_rows)
    
    # Convert period to datetime
    monthly['period'] = pd.to_datetime(monthly['period'])
    
    # Flag missing February 2024 for Mysuru
    mysuru_periods = set(monthly[monthly['city'] == 'Mysuru']['period'].dt.strftime('%Y-%m'))
    if '2024-02' not in mysuru_periods:
        log.warning("Mysuru missing February 2024 in monthly indicators — noted, not imputed")
    
    log.info(f"  Demographics: {len(demographics)} cities")
    log.info(f"  SEC distribution: {len(sec_distribution)} rows")
    log.info(f"  Monthly indicators: {len(monthly)} rows")
    
    return demographics, sec_distribution, monthly

def clean_distribution():
    log.info("Cleaning distribution Excel...")
    
    path = os.path.join(RAW_DIR, 'distribution', 'retail_census.xlsx')
    
    # ── Sheet 1: Store Census ──
    census = pd.read_excel(path, sheet_name='Store Census')
    census['city'] = census['City'].apply(normalise_city)
    census = census.drop(columns=['City'])
    
    # ── Sheet 2: Monthly Channel Coverage ──
    coverage = pd.read_excel(path, sheet_name='Monthly Channel Cov.')
    coverage['city'] = coverage['City'].apply(normalise_city)
    coverage['month'] = pd.to_datetime(coverage['Month'], format='%b-%Y')
    coverage = coverage.drop(columns=['City', 'Month'])
    
    # ── Sheet 3: Infrastructure ──
    infra = pd.read_excel(path, sheet_name='Infrastructure')
    infra['city'] = infra['City'].apply(normalise_city)
    infra = infra.drop(columns=['City'])
    
    # Partner Contacts sheet deliberately skipped — no analytical value
    
    log.info(f"  Store census: {len(census)} rows")
    log.info(f"  Channel coverage: {len(coverage)} rows")
    log.info(f"  Infrastructure: {len(infra)} rows")
    
    return census, coverage, infra

def clean_nielsen():
    log.info("Cleaning Nielsen FMCG report...")
    
    path = os.path.join(RAW_DIR, 'nielsen', 'fmcg_report.xlsx')
    
    # ── Sheet 1: Monthly HH Spend ──
    spend = pd.read_excel(path, sheet_name='Monthly HH Spend')
    spend['city'] = spend['Market'].apply(normalise_city)
    spend['fmcg_category'] = spend['FMCG_Category'].apply(normalise_category)
    spend['period'] = pd.to_datetime(spend['Period'], format='%b-%Y')
    
    # Mysuru spend is weekly — convert to monthly
    weekly_mask = spend['Spend_Period'] == 'Weekly'
    spend.loc[weekly_mask, 'Avg_HH_Spend_INR'] = (
        spend.loc[weekly_mask, 'Avg_HH_Spend_INR'] * 4.33
    ).round(0)
    log.warning(f"  Converted {weekly_mask.sum()} Mysuru weekly spend rows to monthly (×4.33)")
    
    spend = spend.drop(columns=['Market', 'FMCG_Category', 'Period', 'Spend_Period'])
    spend = spend.rename(columns={
        'Avg_HH_Spend_INR': 'avg_hh_spend_monthly_inr',
        'YoY_Growth_%': 'yoy_growth_pct',
        'Category_Penetration_%': 'category_penetration_pct',
    })
    
    # ── Sheet 2: Category Penetration ──
    penetration = pd.read_excel(path, sheet_name='Category Penetration')
    penetration['city'] = penetration['Market'].apply(normalise_city)
    # Category names differ from Sheet 1 — standardise using same map
    penetration['fmcg_category'] = penetration['Category'].apply(normalise_category)
    penetration = penetration.drop(columns=['Market', 'Category'])
    penetration = penetration.rename(columns={
        'Penetration_%': 'penetration_pct',
        'Switching_Index': 'switching_index',
        'Brand_Loyalty_Score_10': 'brand_loyalty_score',
    })
    
    log.info(f"  Monthly spend: {len(spend)} rows")
    log.info(f"  Penetration: {len(penetration)} rows")
    
    return spend, penetration

def clean_competitors():
    log.info("Cleaning competitor intelligence...")
    
    path = os.path.join(RAW_DIR, 'competitor', 'competitor_intelligence.csv')
    df = pd.read_csv(path)
    
    # Normalise city and competitor names
    df['city'] = df['city'].apply(normalise_city)
    df['competitor'] = df['Competitor'].str.strip().str.lower().map(
        lambda x: COMPETITOR_MAP.get(x, x.title())
    )
    
    # Parse market share — remove % sign and convert to float
    df['market_share'] = (
        df['Est_Market_Share']
        .str.replace('%', '', regex=False)
        .astype(float)
        .div(100)
    )
    
    # Normalise shares per city per quarter so they sum to 1.0
    city_quarter_totals = df.groupby(['city', 'Quarter'])['market_share'].transform('sum')
    df['market_share_normalised'] = (df['market_share'] / city_quarter_totals).round(4)
    
    # Log missing quarters for smaller competitors
    total_expected = df['city'].nunique() * len(df['Quarter'].unique()) * df['competitor'].nunique()
    total_actual = len(df)
    log.warning(f"  {total_expected - total_actual} competitor-quarter combinations missing — smaller competitors not reported every quarter")
    
    df = df.drop(columns=['Competitor', 'Est_Market_Share', 'market_share'])
    df = df.rename(columns={
        'Quarter': 'quarter',
        'Distribution_Reach_%': 'distribution_reach_pct',
        'Price_Positioning': 'price_positioning',
        'Promotional_Activity': 'promotional_activity',
        'Price_Index_vs_Category': 'price_index',
        'Years_in_Market': 'years_in_market',
        'Source_Year': 'source_year',
        'Data_Quality_Flag': 'data_quality_flag',
    })
    
    log.info(f"  Competitor data: {len(df)} rows")
    return df

def clean_logistics():
    log.info("Cleaning logistics vendor report...")
    
    path = os.path.join(RAW_DIR, 'logistics', 'vendor_report.csv')
    
    # Read all lines — can't use pd.read_csv() directly on report-style file
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Strip whitespace and split by comma
    rows = [line.strip().split(',') for line in lines]
    
    # ── Extract each section manually ──
    sections = {}
    current_section = None
    header = None
    
    for row in rows:
        # Skip blank rows
        if not any(cell.strip() for cell in row):
            continue
        
        # Detect section headers
        first_cell = row[0].strip().strip('"')
        if first_cell.startswith('SECTION'):
            current_section = ','.join(row).strip().strip('"')
            header = None
            sections[current_section] = {'header': None, 'rows': []}
            continue
        
        # Skip non-data rows — title, notes, end markers
        if any(keyword in row[0] for keyword in ['BLUE DART','Distribution Feasibility','Report','Prepared','Date','END','SUBTOTAL','For queries']):
            continue
        
        # First meaningful row after section header is the column header
        if current_section and header is None:
            header = [col.strip() for col in row]
            sections[current_section]['header'] = header
            continue
        
        # Data rows
        if current_section and header:
            if len(row) >= 3 and row[0].strip() in ['Nashik','Nagpur','Mysuru']:
               sections[current_section]['rows'].append(
    dict(zip(header, [cell.strip() for cell in row]))
)
    
    # ── Build dataframes per section ──
    for i, row in enumerate(rows):
       print(i, row)
    route     = pd.DataFrame(sections['SECTION 1: ROUTE & CONNECTIVITY ANALYSIS']['rows'])
    costs     = pd.DataFrame(sections['SECTION 2: COST STRUCTURE (per MT, INR)']['rows'])
    warehouse = pd.DataFrame(sections['SECTION 3: WAREHOUSING']['rows'])
    risk      = pd.DataFrame(sections['SECTION 4: RISK ASSESSMENT']['rows'])
    
    # ── Merge all sections on City ──
    logistics = route.merge(costs, on='City').merge(warehouse, on='City').merge(risk, on='City')
    
    # Normalise city name
    logistics['city'] = logistics['City'].apply(normalise_city)
    logistics = logistics.drop(columns=['City'])
    
    # Convert numeric columns
    logistics['Distance_km'] = pd.to_numeric(logistics['Distance_km'], errors='coerce')
    logistics['Avg_Transit_hrs_from_Mumbai'] = pd.to_numeric(logistics['Avg_Transit_hrs_from_Mumbai'], errors='coerce')
    logistics['Primary_Freight_INR_per_MT'] = pd.to_numeric(logistics['Primary_Freight_INR_per_MT'], errors='coerce')
    logistics['Last_Mile_Index_10'] = pd.to_numeric(logistics['Last_Mile_Index_10'], errors='coerce')
    
    log.info(f"  Logistics: {len(logistics)} rows, {len(logistics.columns)} columns")
    return logistics

def clean_erp():
    log.info("Cleaning ERP sales data...")
    
    erp_dir = os.path.join(RAW_DIR, 'erp')
    
    # Date formats differ per market
    date_formats = {
        'mumbai':     '%Y-%m-%d',
        'pune':       '%Y-%m-%d',
        'aurangabad': '%d/%m/%Y',
    }
    
    all_frames = []
    
    for market, fmt in date_formats.items():
        fname = f"{market}_sales.csv"
        df = pd.read_csv(os.path.join(erp_dir, fname))
        
        # Parse date using market-specific format
        df['date'] = pd.to_datetime(df['Date'], format=fmt)
        
        # Normalise column names
        df = df.rename(columns={
            'Market':            'market',
            'SKU_Code':          'sku_code',
            'SKU_Name':          'sku_name',
            'Category':          'category',
            'Units_Sold':        'units_sold',
            'MRP_INR':           'mrp_inr',
            'Gross_Revenue_INR': 'gross_revenue_inr',
            'Margin_%':          'margin_pct',
            'Stockout_Flag':     'stockout_flag',
            'Promo_Period':      'promo_period',
            'Promo_Type':        'promo_type',
        })
        
        df['category'] = df['category'].apply(normalise_category)
        df = df.drop(columns=['Date'])
        
        # Log stockout events
        stockouts = df[df['stockout_flag'] == 'Y']
        if len(stockouts) > 0:
            log.warning(f"  {market}: {len(stockouts)} stockout events found")
        
        all_frames.append(df)
    
    erp = pd.concat(all_frames, ignore_index=True)
    
    log.info(f"  ERP combined: {len(erp)} rows across {erp['market'].nunique()} markets")
    return erp

def read_strategy_brief():
    log.info("Reading strategy brief...")
    
    path = os.path.join(RAW_DIR, 'internal', 'strategy_brief.txt')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    log.info(f"  Strategy brief: {len(content)} characters loaded")
    return content

def load_to_sqlite(tables: dict):
    log.info(f"\nLoading to SQLite: {DB_PATH}")
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    for table_name, df in tables.items():
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        log.info(f"  ✓ {table_name} — {len(df)} rows")
    
    conn.close()
    log.info("  Database connection closed")

if __name__ == '__main__':
    log.info("=" * 60)
    log.info("MERIDIAN MARKET ENTRY — ETL PIPELINE")
    log.info(f"Run timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    # ── Extract & Transform ──
    demographics, sec_distribution, monthly_indicators = clean_json()
    census, coverage, infra = clean_distribution()
    spend, penetration = clean_nielsen()
    competitors = clean_competitors()
    logistics = clean_logistics()
    erp = clean_erp()
    strategy_brief = read_strategy_brief()

    # ── Load ──
    tables = {
        'demographics':          demographics,
        'sec_distribution':      sec_distribution,
        'monthly_indicators':    monthly_indicators,
        'store_census':          census,
        'channel_coverage':      coverage,
        'infrastructure':        infra,
        'consumer_spend':        spend,
        'category_penetration':  penetration,
        'competitor_intelligence': competitors,
        'logistics':             logistics,
        'erp_sales':             erp,
    }

    load_to_sqlite(tables)

    log.info("\n" + "=" * 60)
    log.info("ETL COMPLETE — data/database/meridian.db ready")
    log.info("Next: open notebooks/01_EDA.ipynb")
    log.info("=" * 60)

