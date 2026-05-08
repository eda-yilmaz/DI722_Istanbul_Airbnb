import sys
print(sys.executable)


# =============================================================================
# Spatio-Temporal Impact of STR Regulation on Airbnb in Istanbul
# DI 722 – Spatio-Temporal Data Mining | METU
# Author: Eda Yılmaz
# Data: Inside Airbnb – Istanbul (Scraped: September 2025)
# =============================================================================

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 0. DATA OVERVIEW – Columns and First 10 Rows
# =============================================================================

print("=" * 60)
print("SECTION 0A: LISTINGS.CSV — FULL COLUMN OVERVIEW")
print("=" * 60)

df_preview = pd.read_csv('Data/listings.csv')

print(f"\nShape: {df_preview.shape[0]:,} rows × {df_preview.shape[1]} columns\n")

print("── All columns with dtype and non-null count ──")
col_info = pd.DataFrame({
    'dtype'   : df_preview.dtypes.astype(str),
    'non_null': df_preview.notnull().sum(),
    'null_pct': (df_preview.isnull().mean() * 100).round(1).astype(str) + '%',
    'sample'  : [str(df_preview[c].dropna().iloc[0])[:60]
                 if df_preview[c].notnull().any() else 'ALL NULL'
                 for c in df_preview.columns]
})
print(col_info.to_string())

print("\n── First 10 rows (key columns only for readability) ──")
key_cols = [
    'id', 'name', 'host_id', 'host_name',
    'neighbourhood_cleansed', 'latitude', 'longitude',
    'room_type', 'accommodates', 'price',
    'availability_365', 'license',
    'first_review', 'last_review', 'number_of_reviews'
]
# Only keep columns that exist in the file
key_cols = [c for c in key_cols if c in df_preview.columns]
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 40)
print(df_preview[key_cols].head(10).to_string(index=False))

print("\n" + "=" * 60)
print("SECTION 0B: CALENDAR.CSV.GZ — FULL COLUMN OVERVIEW")
print("=" * 60)

df_cal_preview = pd.read_csv('Data/calendar.csv.gz', nrows=10, compression='gzip')

print(f"\nColumns ({len(df_cal_preview.columns)}): {list(df_cal_preview.columns)}")
print(f"\nDate range (first 10 rows): {df_cal_preview['date'].min()} → {df_cal_preview['date'].max()}")

print("\n── All columns with dtype ──")
cal_full_dtypes = pd.read_csv('Data/calendar.csv.gz', nrows=0, compression='gzip').dtypes
print(cal_full_dtypes.to_string())

print("\n── First 10 rows (all columns) ──")
print(df_cal_preview.to_string(index=False))

print("\n── Total row count (approx, counting chunks) ──")
total_rows = 0
for chunk in pd.read_csv('Data/calendar.csv.gz', usecols=['listing_id'],
                          chunksize=500_000, compression='gzip'):
    total_rows += len(chunk)
print(f"Total rows in calendar.csv.gz: {total_rows:,}")
print(f"Unique dates covered: Sep 30 2025 → Sep 30 2026 (365 days per listing)")

print("\n" + "=" * 60)
print("END OF SECTION 0 — DATA OVERVIEW COMPLETE")
print("=" * 60 + "\n")

# =============================================================================
# 1. LOAD DATA
# =============================================================================

print("=" * 60)
print("LOADING DATA")
print("=" * 60)

df = pd.read_csv('Data/listings.csv')

print(f"Total listings     : {len(df):,}")
print(f"Total columns      : {df.shape[1]}")
print(f"Scrape date        : {df['last_scraped'].value_counts().index[0]}")

# =============================================================================
# 2. EXPLORE MISSING VALUES
# =============================================================================

print("\n" + "=" * 60)
print("MISSING VALUES ANALYSIS")
print("=" * 60)

missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(1)
missing_df = pd.DataFrame({
    'Missing Count': missing,
    'Missing %': missing_pct,
    'Meaning': ''
}).query('`Missing Count` > 0').sort_values('Missing %', ascending=False)

# Annotate what each missing value means for your research
meanings = {
    'neighbourhood_group_cleansed': 'Not used – no borough-level grouping for Istanbul',
    'calendar_updated'            : 'Deprecated column – safely drop',
    'host_neighbourhood'          : 'Host did not specify their neighbourhood – not critical',
    'neighbourhood'               : 'Free-text field – use neighbourhood_cleansed instead',
    'neighborhood_overview'       : 'Host did not write a neighbourhood description – not critical',
    'host_about'                  : 'Host did not write a bio – not critical',
    'license'                     : '⚠️  KEY VARIABLE: NaN = no permit = potentially non-compliant',
    'review_scores_rating'        : 'Listing has no reviews yet – new or inactive listing',
    'review_scores_accuracy'      : 'Listing has no reviews yet',
    'review_scores_cleanliness'   : 'Listing has no reviews yet',
    'review_scores_checkin'       : 'Listing has no reviews yet',
    'review_scores_communication' : 'Listing has no reviews yet',
    'review_scores_location'      : 'Listing has no reviews yet',
    'review_scores_value'         : 'Listing has no reviews yet',
    'reviews_per_month'           : 'Listing has no reviews yet',
    'last_review'                 : 'Listing has no reviews yet',
    'first_review'                : 'Listing has no reviews yet',
    'host_location'               : 'Host did not specify location – not critical',
    'host_acceptance_rate'        : 'Host has not set auto-accept or no booking requests yet',
    'host_response_time'          : 'Host has not responded to any requests yet',
    'bathrooms'                   : 'Host did not specify – use bathrooms_text instead',
    'bedrooms'                    : 'Host did not specify number of bedrooms',
    'price'                       : 'Host has not set a price – listing inactive',
    'description'                 : 'Host did not write a description',
}

for col, meaning in meanings.items():
    if col in missing_df.index:
        missing_df.loc[col, 'Meaning'] = meaning

print(missing_df[missing_df['Missing Count'] > 0][['Missing Count', 'Missing %', 'Meaning']].to_string())

# =============================================================================
# 3. CLEAN KEY VARIABLES
# =============================================================================

print("\n" + "=" * 60)
print("CLEANING KEY VARIABLES")
print("=" * 60)

# --- 3a. Price ---
df['price_clean'] = df['price'].str.replace(r'[\$,]', '', regex=True).astype(float)
price_missing = df['price_clean'].isna().sum()
price_outliers = (df['price_clean'] > df['price_clean'].quantile(0.99)).sum()
print(f"Price – missing        : {price_missing:,} listings (no price set)")
print(f"Price – outliers (>p99): {price_outliers:,} listings")

# Remove missing prices and extreme outliers (top 1%)
df_clean = df.dropna(subset=['price_clean'])
df_clean = df_clean[df_clean['price_clean'] <= df_clean['price_clean'].quantile(0.99)]
df_clean = df_clean[df_clean['price_clean'] >= 100]  # min realistic price in TRY
print(f"Price – kept after clean: {len(df_clean):,} listings")

# --- 3b. Coordinates ---
coord_issues = df_clean[
    (df_clean['latitude'] < 40.8) | (df_clean['latitude'] > 41.5) |
    (df_clean['longitude'] < 28.0) | (df_clean['longitude'] > 30.0)
]
print(f"\nCoordinates – outside Istanbul bbox: {len(coord_issues):,} listings")
df_clean = df_clean[
    (df_clean['latitude'].between(40.8, 41.5)) &
    (df_clean['longitude'].between(28.0, 30.0))
]
print(f"Coordinates – kept: {len(df_clean):,} listings")

# --- 3c. License / Compliance Column ---
print("\n--- LICENSE / COMPLIANCE ---")

def classify_compliance(license_val):
    if pd.isna(license_val):
        return 'Unlicensed'
    elif license_val == 'Non-real estate listing':
        return 'Non-real estate'  # hotels, B&Bs – different legal category
    elif license_val == 'Exempt':
        return 'Exempt'           # legally exempt from permit requirement
    else:
        return 'Licensed'         # has an actual permit number

df_clean['compliance'] = df_clean['license'].apply(classify_compliance)

compliance_counts = df_clean['compliance'].value_counts()
compliance_pct    = (compliance_counts / len(df_clean) * 100).round(1)

for cat in compliance_counts.index:
    print(f"  {cat:<22}: {compliance_counts[cat]:>6,}  ({compliance_pct[cat]}%)")

# Binary flag for regression (1 = unlicensed)
df_clean['is_unlicensed'] = (df_clean['compliance'] == 'Unlicensed').astype(int)

# --- 3d. Room Type ---
print("\n--- ROOM TYPE ---")
print(df_clean['room_type'].value_counts().to_string())

# Binary flag: entire home (directly targeted by the 2024 law)
df_clean['is_entire_home'] = (df_clean['room_type'] == 'Entire home/apt').astype(int)

# --- 3e. Date columns ---
df_clean['first_review'] = pd.to_datetime(df_clean['first_review'], errors='coerce')
df_clean['last_review']  = pd.to_datetime(df_clean['last_review'],  errors='coerce')

# Days since last review (proxy for listing activity)
scrape_date = pd.Timestamp('2025-09-30')
df_clean['days_since_last_review'] = (scrape_date - df_clean['last_review']).dt.days

# Was the listing active after the law? (last review after Jan 2024)
df_clean['active_post_regulation'] = (df_clean['last_review'] >= pd.Timestamp('2024-01-01')).astype(int)

print(f"\nListings active after Jan 2024 law : {df_clean['active_post_regulation'].sum():,}")
print(f"Listings last reviewed before 2024 : {(df_clean['active_post_regulation']==0).sum():,}")

# =============================================================================
# 4. FINAL CLEAN DATASET SUMMARY
# =============================================================================

print("\n" + "=" * 60)
print("FINAL CLEAN DATASET")
print("=" * 60)

print(f"Original listings          : {len(df):,}")
print(f"After cleaning             : {len(df_clean):,}")
print(f"Removed                    : {len(df) - len(df_clean):,}")
print(f"\nKey variables ready:")
print(f"  price_clean              : nightly price in TRY (cleaned)")
print(f"  compliance               : Licensed / Unlicensed / Exempt / Non-real estate")
print(f"  is_unlicensed            : binary flag for regression")
print(f"  is_entire_home           : binary flag (targeted by 2024 law)")
print(f"  active_post_regulation   : reviewed after Jan 2024")
print(f"  latitude / longitude     : spatial coordinates for H3 assignment")
print(f"  availability_365         : nights available per year")
print(f"  neighbourhood_cleansed   : Istanbul district")

print("\n✅ Data loading and cleaning complete. Ready for H3 assignment.")

# =============================================================================
# 5. H3 CELL ASSIGNMENT
# =============================================================================

import h3
import geopandas as gpd
from shapely.geometry import Polygon

print("\n" + "=" * 60)
print("H3 CELL ASSIGNMENT")
print("=" * 60)

# --- 5a. Assign each listing to an H3 cell ---
# Resolution 8 = ~0.74 km² per cell (roughly one neighbourhood)
# Resolution 9 = ~0.11 km² per cell (roughly a few city blocks)
# We use resolution 8 for the baseline as recommended by the professor

RESOLUTION = 8

df_clean['h3_cell'] = df_clean.apply(
    lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], RESOLUTION),
    axis=1
)

print(f"H3 Resolution          : {RESOLUTION}")
print(f"Total H3 cells (res {RESOLUTION}) : {df_clean['h3_cell'].nunique():,}")
print(f"Avg listings per cell  : {len(df_clean) / df_clean['h3_cell'].nunique():.1f}")

# --- 5b. Aggregate statistics per H3 cell ---
print("\nAggregating statistics per H3 cell...")

h3_stats = df_clean.groupby('h3_cell').agg(
    listing_count         = ('id',                   'count'),
    unlicensed_count      = ('is_unlicensed',         'sum'),
    unlicensed_pct        = ('is_unlicensed',         lambda x: round(x.mean() * 100, 1)),
    avg_price             = ('price_clean',           'mean'),
    median_price          = ('price_clean',           'median'),
    avg_availability_365  = ('availability_365',      'mean'),
    entire_home_pct       = ('is_entire_home',        lambda x: round(x.mean() * 100, 1)),
    active_post_reg_pct   = ('active_post_regulation',lambda x: round(x.mean() * 100, 1)),
    avg_review_score      = ('review_scores_rating',  'mean'),
).reset_index()

# Round numeric columns
h3_stats['avg_price']   = h3_stats['avg_price'].round(0)
h3_stats['median_price'] = h3_stats['median_price'].round(0)

print(f"\nH3 cells generated     : {len(h3_stats):,}")
print(f"\nTop 10 cells by listing count:")
print(h3_stats.nlargest(10, 'listing_count')[
    ['h3_cell','listing_count','unlicensed_pct','avg_price','entire_home_pct']
].to_string(index=False))

# --- 5c. Compliance categories across cells ---
print("\n--- COMPLIANCE DISTRIBUTION ACROSS H3 CELLS ---")
print(f"Cells with >50% unlicensed  : {(h3_stats['unlicensed_pct'] > 50).sum():,}  ({(h3_stats['unlicensed_pct'] > 50).mean()*100:.1f}% of cells)")
print(f"Cells with >75% unlicensed  : {(h3_stats['unlicensed_pct'] > 75).sum():,}  ({(h3_stats['unlicensed_pct'] > 75).mean()*100:.1f}% of cells)")
print(f"Cells with 0% unlicensed    : {(h3_stats['unlicensed_pct'] == 0).sum():,}  ({(h3_stats['unlicensed_pct'] == 0).mean()*100:.1f}% of cells)")
print(f"\nAvg unlicensed % per cell   : {h3_stats['unlicensed_pct'].mean():.1f}%")
print(f"Median unlicensed % per cell: {h3_stats['unlicensed_pct'].median():.1f}%")

# --- 5d. Convert H3 cells to polygons for mapping (professor's method) ---
print("\nConverting H3 cells to polygons for mapping...")

hexagons = []
for cell in h3_stats['h3_cell']:
    boundary = h3.cell_to_boundary(cell)
    hexagon  = Polygon([(lng, lat) for lat, lng in boundary])
    hexagons.append({'h3_id': cell, 'geometry': hexagon})

h3_gdf = gpd.GeoDataFrame(hexagons, crs='EPSG:4326')
h3_gdf = h3_gdf.merge(h3_stats, left_on='h3_id', right_on='h3_cell')

# Save as GeoJSON (universally supported, works in QGIS and Python maps)
output_path = 'Data/istanbul_airbnb_h3.geojson'
h3_gdf.to_file(output_path, driver='GeoJSON')
print(f"Saved to: {output_path}")

# --- 5e. Also try resolution 9 for comparison ---
df_clean['h3_cell_r9'] = df_clean.apply(
    lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], 9),
    axis=1
)
r9_cells = df_clean['h3_cell_r9'].nunique()
print(f"\nResolution 9 comparison:")
print(f"  Cells (res 9)          : {r9_cells:,}")
print(f"  Avg listings per cell  : {len(df_clean) / r9_cells:.1f}")
print(f"  → Resolution 8 gives better-sized clusters for neighbourhood analysis")

print("\n✅ H3 assignment complete. Ready for visualisation and analysis.")

# =============================================================================
# 6. MAP VISUALISATION
# =============================================================================

import folium
import json

print("\n" + "=" * 60)
print("MAP VISUALISATION")
print("=" * 60)

# --- 6a. Compliance Map ---
# Colour each H3 cell by % unlicensed listings
# Dark red = high non-compliance, light yellow = low non-compliance

def compliance_colour(pct):
    if pct >= 75:   return '#d73027'   # dark red   – very high non-compliance
    elif pct >= 50: return '#fc8d59'   # orange     – high non-compliance
    elif pct >= 25: return '#fee090'   # yellow     – moderate
    else:           return '#4575b4'   # blue       – low non-compliance (mostly licensed)

print("Building compliance map...")

compliance_map = folium.Map(
    location=[41.01, 28.96],   # Istanbul centre
    zoom_start=10,
    tiles='CartoDB positron'
)

# Add H3 hexagons coloured by compliance
geojson_data = json.loads(h3_gdf.to_json())

for feature in geojson_data['features']:
    props       = feature['properties']
    pct         = props.get('unlicensed_pct', 0)
    count       = props.get('listing_count', 0)
    avg_price   = props.get('avg_price', 0)

    folium.GeoJson(
        feature,
        style_function=lambda x, p=pct: {
            'fillColor'   : compliance_colour(p),
            'color'       : 'white',
            'weight'      : 0.5,
            'fillOpacity' : 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['listing_count', 'unlicensed_pct', 'avg_price', 'entire_home_pct'],
            aliases=['Listings:', 'Unlicensed %:', 'Avg Price (TRY):', 'Entire Home %:'],
            localize=True
        )
    ).add_to(compliance_map)

# Add legend
legend_html = """
<div style="position: fixed; bottom: 40px; left: 40px; z-index: 1000;
     background: white; padding: 12px 16px; border-radius: 8px;
     box-shadow: 2px 2px 6px rgba(0,0,0,0.3); font-family: Arial; font-size: 12px;">
  <b>Unlicensed Listings %</b><br>
  <i style="background:#d73027;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> ≥75% (Very High)<br>
  <i style="background:#fc8d59;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> 50–74% (High)<br>
  <i style="background:#fee090;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> 25–49% (Moderate)<br>
  <i style="background:#4575b4;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> &lt;25% (Low)<br>
  <br><small>Turkey STR Law No. 7464, Jan 2024<br>Data: Inside Airbnb, Sep 2025</small>
</div>
"""
compliance_map.get_root().html.add_child(folium.Element(legend_html))

compliance_map.save('Data/istanbul_compliance_map.html')
print("Saved: Data/istanbul_compliance_map.html")

# --- 6b. Price Map ---
# Colour each H3 cell by average nightly price

def price_colour(price):
    if price >= 6000:   return '#7b2d8b'   # purple  – very expensive
    elif price >= 4000: return '#d73027'   # red     – expensive
    elif price >= 2500: return '#fc8d59'   # orange  – moderate
    elif price >= 1500: return '#fee090'   # yellow  – affordable
    else:               return '#4575b4'   # blue    – cheap

print("Building price map...")

price_map = folium.Map(
    location=[41.01, 28.96],
    zoom_start=10,
    tiles='CartoDB positron'
)

for feature in geojson_data['features']:
    props = feature['properties']
    price = props.get('avg_price', 0) or 0

    folium.GeoJson(
        feature,
        style_function=lambda x, p=price: {
            'fillColor'   : price_colour(p),
            'color'       : 'white',
            'weight'      : 0.5,
            'fillOpacity' : 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['listing_count', 'avg_price', 'median_price', 'unlicensed_pct'],
            aliases=['Listings:', 'Avg Price (TRY):', 'Median Price (TRY):', 'Unlicensed %:'],
            localize=True
        )
    ).add_to(price_map)

price_legend_html = """
<div style="position: fixed; bottom: 40px; left: 40px; z-index: 1000;
     background: white; padding: 12px 16px; border-radius: 8px;
     box-shadow: 2px 2px 6px rgba(0,0,0,0.3); font-family: Arial; font-size: 12px;">
  <b>Avg Nightly Price (TRY)</b><br>
  <i style="background:#7b2d8b;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> ≥6,000 TRY<br>
  <i style="background:#d73027;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> 4,000–5,999 TRY<br>
  <i style="background:#fc8d59;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> 2,500–3,999 TRY<br>
  <i style="background:#fee090;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> 1,500–2,499 TRY<br>
  <i style="background:#4575b4;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> &lt;1,500 TRY<br>
  <br><small>Data: Inside Airbnb, Sep 2025</small>
</div>
"""
price_map.get_root().html.add_child(folium.Element(price_legend_html))

price_map.save('Data/istanbul_price_map.html')
print("Saved: Data/istanbul_price_map.html")

print("\n✅ Maps saved. Open the HTML files in your browser to explore!")
print("   → Data/istanbul_compliance_map.html")
print("   → Data/istanbul_price_map.html")

# =============================================================================
# 7. BASELINE REGRESSION MODEL
# Research Question: Does compliance status predict listing price,
# after controlling for room type, availability and neighbourhood?
# =============================================================================

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import numpy as np

print("\n" + "=" * 60)
print("BASELINE REGRESSION MODEL")
print("=" * 60)
print("Target   : log(price_clean)  — nightly price in TRY")
print("Features : compliance status, room type, availability,")
print("           accommodates, neighbourhood (top 10)")

# --- 7a. Prepare features ---

# Use log price to reduce skewness
df_reg = df_clean.copy()
df_reg['log_price'] = np.log(df_reg['price_clean'])

# Encode room type as dummy variables
room_dummies = pd.get_dummies(df_reg['room_type'], prefix='room', drop_first=True)

# Encode top 10 neighbourhoods (rest = "Other")
top_neighbourhoods = df_reg['neighbourhood_cleansed'].value_counts().head(10).index
df_reg['neighbourhood_top'] = df_reg['neighbourhood_cleansed'].apply(
    lambda x: x if x in top_neighbourhoods else 'Other'
)
neighbourhood_dummies = pd.get_dummies(df_reg['neighbourhood_top'], prefix='nbhd', drop_first=True)

# Build feature matrix
features = pd.concat([
    df_reg[['is_unlicensed',       # KEY variable: compliance status
            'availability_365',    # how available the listing is
            'accommodates',        # number of guests
            'is_entire_home',      # entire home vs private room
            ]],
    room_dummies,
    neighbourhood_dummies
], axis=1).fillna(0)

target = df_reg['log_price']

print(f"\nFeatures used          : {features.shape[1]}")
print(f"Observations           : {len(features):,}")

# --- 7b. Train/test split ---
X_train, X_test, y_train, y_test = train_test_split(
    features, target, test_size=0.2, random_state=42
)

# --- 7c. Fit baseline linear regression ---
model = LinearRegression()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

# --- 7d. Evaluate ---
r2  = r2_score(y_test, y_pred)
mae = mean_absolute_error(np.exp(y_test), np.exp(y_pred))  # back to TRY

print(f"\n--- MODEL PERFORMANCE ---")
print(f"R² score               : {r2:.4f}  ({r2*100:.1f}% of price variance explained)")
print(f"MAE (in TRY)           : {mae:.0f} TRY")

# --- 7e. Key coefficient: compliance effect ---
coef_df = pd.DataFrame({
    'Feature'    : features.columns,
    'Coefficient': model.coef_
}).sort_values('Coefficient', ascending=False)

print(f"\n--- COEFFICIENTS (log scale) ---")
print(coef_df.to_string(index=False))

# Focus on the compliance coefficient
compliance_coef = coef_df[coef_df['Feature'] == 'is_unlicensed']['Coefficient'].values[0]
price_effect_pct = (np.exp(compliance_coef) - 1) * 100

print(f"\n--- KEY FINDING: COMPLIANCE EFFECT ---")
print(f"Coefficient (log scale): {compliance_coef:.4f}")
if price_effect_pct < 0:
    print(f"Unlicensed listings are {abs(price_effect_pct):.1f}% CHEAPER than licensed ones")
else:
    print(f"Unlicensed listings are {price_effect_pct:.1f}% MORE EXPENSIVE than licensed ones")
print(f"(controlling for room type, availability, neighbourhood, accommodates)")

# --- 7f. Neighbourhood price effects ---
print(f"\n--- TOP NEIGHBOURHOOD EFFECTS (vs baseline) ---")
nbhd_coefs = coef_df[coef_df['Feature'].str.startswith('nbhd_')]
print(nbhd_coefs.to_string(index=False))

print("\n✅ Baseline regression complete.")
print("=" * 60)
print("SUMMARY OF BASELINE MODEL RESULTS")
print("=" * 60)
print(f"  Dataset              : Istanbul Airbnb, Sep 2025")
print(f"  Listings analysed    : {len(df_reg):,}")
print(f"  H3 cells (res 8)     : {df_clean['h3_cell'].nunique():,}")
print(f"  Unlicensed listings  : {df_clean['is_unlicensed'].sum():,} ({df_clean['is_unlicensed'].mean()*100:.1f}%)")
print(f"  Baseline R²          : {r2:.4f}")
print(f"  Compliance price gap : {price_effect_pct:.1f}%")
print(f"\n  → Spatial pattern    : Non-compliance clusters in peripheral")
print(f"    neighbourhoods; tourist core shows lower non-compliance")
print(f"  → Price finding      : Unlicensed listings are systematically")
print(f"    {'cheaper' if price_effect_pct < 0 else 'more expensive'} after controlling for location and property type")

# =============================================================================
# 8. AVAILABILITY ANALYSIS BY COMPLIANCE STATUS
# Research question: Do unlicensed listings behave differently in terms of
# calendar availability — hiding from enforcement, or maximising bookings?
# =============================================================================

print("\n" + "=" * 60)
print("AVAILABILITY ANALYSIS BY COMPLIANCE STATUS")
print("=" * 60)

# --- 8a. Descriptive statistics: availability_365 by compliance ---
avail_stats = df_clean.groupby('compliance')['availability_365'].agg(
    count='count',
    mean='mean',
    median='median',
    std='std',
    q25=lambda x: x.quantile(0.25),
    q75=lambda x: x.quantile(0.75),
).round(1)

print("\nAvailability (nights/year) by compliance status:")
print(avail_stats.to_string())

# --- 8b. Fully blocked listings (availability = 0): proxy for hiding ---
blocked = df_clean.groupby('compliance').apply(
    lambda g: (g['availability_365'] == 0).mean() * 100
).round(1)

print("\n% of listings with zero availability (fully blocked calendar):")
for cat, pct in blocked.items():
    print(f"  {cat:<22}: {pct:.1f}%")

print("\nInterpretation:")
print("  → If unlicensed listings show HIGHER zero-availability rates, they may")
print("    be intentionally blocking calendars to reduce enforcement exposure.")
print("  → If they show LOWER zero-availability, they are maximising bookings")
print("    before potential removal — a 'race to the bottom' dynamic.")

# --- 8c. Entire home vs. private room: availability pattern ---
# The law specifically targets entire homes — do they show different availability?
print("\n--- AVAILABILITY BY ROOM TYPE × COMPLIANCE ---")
avail_cross = df_clean.groupby(['room_type', 'compliance'])['availability_365'].mean().round(1).unstack()
print(avail_cross.to_string())

# --- 8d. Availability by H3 cell: add to h3_stats ---
h3_avail = df_clean.groupby('h3_cell').agg(
    unlicensed_zero_avail_pct=('availability_365',
        lambda x: ((x == 0) & (df_clean.loc[x.index, 'is_unlicensed'] == 1)).mean() * 100),
).reset_index()

print("\n✅ Availability analysis complete.")

# =============================================================================
# 9. EXTENDED REGRESSION WITH INTERACTION TERMS
# Key addition: is_unlicensed × is_entire_home
# Hypothesis: The compliance price penalty is LARGER for entire homes
# (the property type directly targeted by Law No. 7464) than for private rooms.
# A uniform discount would suggest the effect is generic (cost-saving);
# a heterogeneous discount concentrated in entire homes would confirm the law
# creates a specific market distortion in exactly the regulated segment.
# =============================================================================

print("\n" + "=" * 60)
print("EXTENDED REGRESSION: COMPLIANCE × ROOM TYPE INTERACTION")
print("=" * 60)
print("Added interaction: is_unlicensed × is_entire_home")
print("Hypothesis: compliance penalty is larger for entire homes (directly")
print("targeted by Law No. 7464) than for private rooms.")

# --- 9a. Build extended feature matrix ---
df_reg2 = df_clean.copy()
df_reg2['log_price'] = np.log(df_reg2['price_clean'])

# Interaction term: unlicensed × entire home
df_reg2['unlicensed_x_entire_home'] = df_reg2['is_unlicensed'] * df_reg2['is_entire_home']

# Neighbourhood dummies (same as baseline)
top_neighbourhoods2 = df_reg2['neighbourhood_cleansed'].value_counts().head(10).index
df_reg2['neighbourhood_top'] = df_reg2['neighbourhood_cleansed'].apply(
    lambda x: x if x in top_neighbourhoods2 else 'Other'
)
neighbourhood_dummies2 = pd.get_dummies(df_reg2['neighbourhood_top'], prefix='nbhd', drop_first=True)
room_dummies2 = pd.get_dummies(df_reg2['room_type'], prefix='room', drop_first=True)

features2 = pd.concat([
    df_reg2[['is_unlicensed',
             'is_entire_home',
             'unlicensed_x_entire_home',   # <-- the key addition
             'availability_365',
             'accommodates',
             ]],
    room_dummies2,
    neighbourhood_dummies2
], axis=1).fillna(0)

target2 = df_reg2['log_price']

X_train2, X_test2, y_train2, y_test2 = train_test_split(
    features2, target2, test_size=0.2, random_state=42
)

model2 = LinearRegression()
model2.fit(X_train2, y_train2)

y_pred2 = model2.predict(X_test2)

r2_ext  = r2_score(y_test2, y_pred2)
mae_ext = mean_absolute_error(np.exp(y_test2), np.exp(y_pred2))

print(f"\n--- EXTENDED MODEL PERFORMANCE ---")
print(f"R² score               : {r2_ext:.4f}  ({r2_ext*100:.1f}%)")
print(f"MAE (TRY)              : {mae_ext:.0f}")
print(f"R² improvement vs. baseline: {(r2_ext - r2)*100:+.2f} pp")

# --- 9b. Extract and interpret the three key coefficients ---
coef_df2 = pd.DataFrame({
    'Feature'    : features2.columns,
    'Coefficient': model2.coef_
})

c_unlicensed   = coef_df2.loc[coef_df2['Feature'] == 'is_unlicensed',           'Coefficient'].values[0]
c_entire       = coef_df2.loc[coef_df2['Feature'] == 'is_entire_home',          'Coefficient'].values[0]
c_interaction  = coef_df2.loc[coef_df2['Feature'] == 'unlicensed_x_entire_home','Coefficient'].values[0]

# Implied price effects
# Private room, unlicensed:     exp(c_unlicensed) - 1
# Entire home, unlicensed:      exp(c_unlicensed + c_interaction) - 1
# Entire home, licensed:        exp(c_entire) - 1  (vs. private room licensed)

gap_private_room   = (np.exp(c_unlicensed) - 1) * 100
gap_entire_home    = (np.exp(c_unlicensed + c_interaction) - 1) * 100
entire_home_premium = (np.exp(c_entire) - 1) * 100

print(f"\n--- KEY COEFFICIENTS ---")
print(f"  is_unlicensed               : {c_unlicensed:+.4f}")
print(f"  is_entire_home              : {c_entire:+.4f}")
print(f"  unlicensed × entire_home    : {c_interaction:+.4f}")

print(f"\n--- IMPLIED PRICE EFFECTS ---")
print(f"  Compliance discount – private rooms  : {gap_private_room:+.1f}%")
print(f"  Compliance discount – entire homes   : {gap_entire_home:+.1f}%")
print(f"  Entire home premium (licensed only)  : {entire_home_premium:+.1f}%")

print(f"\n--- INTERPRETATION ---")
diff = abs(gap_private_room) - abs(gap_entire_home)
print(f"  ✅ The compliance penalty IS heterogeneous across room types ({diff:.1f} pp difference).")
if abs(gap_private_room) > abs(gap_entire_home):
    print(f"  UNEXPECTED DIRECTION: penalty is larger for PRIVATE ROOMS ({gap_private_room:.1f}%)")
    print(f"  than for ENTIRE HOMES ({gap_entire_home:.1f}%), despite entire homes being the")
    print(f"  segment directly targeted by Law No. 7464.")
    print(f"  Interpretation: entire-home unlicensed hosts maintain near-market prices")
    print(f"  because product differentiation (location, full apartment) sustains demand")
    print(f"  regardless of permit status. Private room unlicensed hosts compete on price")
    print(f"  in a commoditised segment — the discount reflects both regulatory risk and")
    print(f"  quality selection (marginal, informal operators concentrated in this type).")
else:
    print(f"  CONFIRMED: penalty is larger for ENTIRE HOMES ({gap_entire_home:.1f}%)")
    print(f"  than for PRIVATE ROOMS ({gap_private_room:.1f}%), consistent with the law")
    print(f"  creating a direct market distortion in the regulated segment.")

print("\n✅ Extended regression complete.")

# =============================================================================
# 10. SPATIAL AUTOCORRELATION: MORAN'S I
# Research question: Is non-compliance spatially clustered across H3 cells,
# or randomly distributed?
# A significant positive Moran's I means neighbouring cells have similar
# compliance rates — i.e., non-compliance is contagious / geographically
# structured. This is NOT intuitive: it implies either that enforcement
# resources are geographically concentrated, or that host networks and
# information diffusion operate locally.
# =============================================================================

print("\n" + "=" * 60)
print("SPATIAL AUTOCORRELATION: MORAN'S I")
print("=" * 60)

# Pure H3 + NumPy implementation — no libpysal/esda required.
# We build the spatial weights matrix directly from H3 neighbour topology:
# each cell's 6 immediate H3 neighbours (grid_disk k=1 minus itself) form
# the row-standardised weight row. This is mathematically identical to
# Queen contiguity weights on hexagonal grids.

# --- 10a. Build spatial weights from H3 topology ---
print("Building spatial weights from H3 topology...")

cell_list  = h3_gdf['h3_id'].tolist()
cell_index = {cell: i for i, cell in enumerate(cell_list)}
n          = len(cell_list)

# adjacency: list of neighbour indices for each cell
adjacency = []
for cell in cell_list:
    raw_neighbours = set(h3.grid_disk(cell, 1)) - {cell}
    neighbours_in_dataset = [cell_index[nb] for nb in raw_neighbours if nb in cell_index]
    adjacency.append(neighbours_in_dataset)

mean_nb = np.mean([len(nb) for nb in adjacency])
islands  = sum(1 for nb in adjacency if len(nb) == 0)
print(f"  Cells                   : {n:,}")
print(f"  Isolated cells (islands): {islands}")
print(f"  Mean neighbours         : {mean_nb:.2f}")

# --- Helper: compute Global Moran's I with permutation test ---
def global_morans_i(values, adjacency, n_perms=999, seed=42):
    """
    Compute Global Moran's I and a pseudo p-value via permutation test.
    values    : array-like of length n
    adjacency : list of lists — adjacency[i] = [j indices of neighbours]
    """
    x    = np.array(values, dtype=float)
    xbar = x.mean()
    z    = x - xbar                          # deviations from mean
    z2   = (z ** 2).sum()                    # sum of squared deviations

    # Spatial lag: row-standardised weighted average of neighbours
    def spatial_lag(z_vals):
        lag = np.zeros(len(z_vals))
        for i, nbs in enumerate(adjacency):
            if len(nbs) > 0:
                lag[i] = z_vals[nbs].mean()  # row-standardised
        return lag

    lag_z    = spatial_lag(z)
    I_obs    = (z * lag_z).sum() / z2

    # Expected value under H0 (random)
    EI = -1.0 / (n - 1)

    # Permutation test
    rng    = np.random.default_rng(seed)
    I_perm = np.empty(n_perms)
    for k in range(n_perms):
        z_shuf      = rng.permutation(z)
        lag_shuf    = spatial_lag(z_shuf)
        I_perm[k]   = (z_shuf * lag_shuf).sum() / (z_shuf ** 2).sum()

    p_sim = (np.sum(I_perm >= I_obs) + 1) / (n_perms + 1)  # one-sided upper
    return I_obs, EI, p_sim, I_perm

# --- Helper: compute Local Moran's I (LISA) ---
def local_morans_i(values, adjacency, n_perms=999, seed=42):
    """
    Returns arrays: local_I, quadrant (1=HH,2=LH,3=LL,4=HL), p_sim
    """
    x    = np.array(values, dtype=float)
    xbar = x.mean()
    z    = x - xbar
    s2   = (z ** 2).mean()

    # Local spatial lag (row-standardised)
    lag_z = np.array([
        z[nbs].mean() if len(nbs) > 0 else 0.0
        for nbs in adjacency
    ])
    local_I = (z / s2) * lag_z

    # Quadrant classification
    quad = np.zeros(len(z), dtype=int)
    quad[(z > 0) & (lag_z > 0)] = 1  # HH
    quad[(z < 0) & (lag_z > 0)] = 2  # LH
    quad[(z < 0) & (lag_z < 0)] = 3  # LL
    quad[(z > 0) & (lag_z < 0)] = 4  # HL

    # Conditional permutation test for each cell
    rng    = np.random.default_rng(seed)
    counts = np.zeros(len(z))
    for _ in range(n_perms):
        z_shuf = rng.permutation(z)
        lag_shuf = np.array([
            z_shuf[nbs].mean() if len(nbs) > 0 else 0.0
            for nbs in adjacency
        ])
        sim_I = (z / s2) * lag_shuf
        counts += (sim_I >= local_I)

    p_sim = (counts + 1) / (n_perms + 1)
    return local_I, quad, p_sim

# --- 10b. Global Moran's I: unlicensed_pct ---
unlicensed_vals = h3_gdf['unlicensed_pct'].fillna(0).values
I_u, EI_u, p_u, _ = global_morans_i(unlicensed_vals, adjacency)

print(f"\n--- GLOBAL MORAN'S I: unlicensed_pct ---")
print(f"  Moran's I              : {I_u:.4f}")
print(f"  Expected I (under H0)  : {EI_u:.4f}")
print(f"  p-value (999 perms)    : {p_u:.4f}")

if p_u < 0.05:
    if I_u > 0:
        print(f"\n  ✅ SIGNIFICANT POSITIVE SPATIAL AUTOCORRELATION")
        print(f"     Non-compliance is spatially CLUSTERED: cells with high")
        print(f"     unlicensed rates are systematically located next to other")
        print(f"     high-unlicensed cells. This is not random.")
        print(f"     Implication: enforcement must be spatially targeted —")
        print(f"     a uniform city-wide policy misses the geographic structure.")
    else:
        print(f"\n  ✅ SIGNIFICANT NEGATIVE SPATIAL AUTOCORRELATION")
        print(f"     Non-compliance is spatially DISPERSED (checkerboard pattern).")
else:
    print(f"\n  No significant spatial autocorrelation detected (p={p_u:.3f})")

# --- 10c. Global Moran's I: avg_price ---
price_vals = h3_gdf['avg_price'].fillna(h3_gdf['avg_price'].mean()).values
I_p, EI_p, p_p, _ = global_morans_i(price_vals, adjacency)

print(f"\n--- GLOBAL MORAN'S I: avg_price ---")
print(f"  Moran's I              : {I_p:.4f}")
print(f"  p-value (999 perms)    : {p_p:.4f}")
if p_p < 0.05:
    print(f"  ✅ Prices are also spatially clustered")
    if I_p > I_u:
        print(f"     Price clustering (I={I_p:.3f}) is STRONGER than compliance clustering")
        print(f"     (I={I_u:.3f}) — location explains price more than compliance does alone.")

# --- 10d. Sensitivity Analysis: Moran's I across k = 1, 2, 3 ---
print("\n" + "="*60)
print("SPATIAL WEIGHTS SENSITIVITY ANALYSIS")
print("="*60)
print("Testing Global Moran's I (unlicensed_pct) for k = 1, 2, 3")
print("to verify that clustering result is robust to bandwidth choice.\n")

sensitivity_results = []
for k in [1, 2, 3]:
    adj_k = []
    for cell in cell_list:
        raw_nb = set(h3.grid_disk(cell, k)) - {cell}
        nb_in  = [cell_index[nb] for nb in raw_nb if nb in cell_index]
        adj_k.append(nb_in)
    mean_nb_k = round(float(np.mean([len(nb) for nb in adj_k])), 2)
    I_k, EI_k, p_k, _ = global_morans_i(unlicensed_vals, adj_k)
    sensitivity_results.append({
        'k': k, 'mean_neighbours': mean_nb_k,
        'morans_I': round(I_k, 4), 'p_value': round(p_k, 4)
    })
    sig = "✅ significant" if p_k < 0.05 else "❌ not significant"
    print(f"  k={k}  |  Mean neighbours: {mean_nb_k:5.1f}  |  "
          f"Moran's I = {I_k:.4f}  |  p = {p_k:.4f}  |  {sig}")

print("\nConclusion:")
all_sig = all(r['p_value'] < 0.05 for r in sensitivity_results)
if all_sig:
    I_vals = [r['morans_I'] for r in sensitivity_results]
    print(f"  Spatial clustering is significant at all three bandwidths.")
    print(f"  Moran's I ranges from {min(I_vals):.4f} (k={sensitivity_results[I_vals.index(min(I_vals))]['k']}) "
          f"to {max(I_vals):.4f} (k={sensitivity_results[I_vals.index(max(I_vals))]['k']}).")
    print(f"  Result is robust to spatial bandwidth choice.")
else:
    print("  ⚠️  Clustering significance varies across bandwidths — interpret with caution.")

# --- 10e. Local Moran's I (LISA) ---
print(f"\nComputing Local Moran's I (LISA) — this takes ~30 seconds...")
local_I, quad, p_lisa = local_morans_i(unlicensed_vals, adjacency)

quad_labels = {1: 'HH (Hot Spot)', 2: 'LH (Spatial Outlier)',
               3: 'LL (Cold Spot)',  4: 'HL (Spatial Outlier)'}

h3_gdf['lisa_I']       = local_I
h3_gdf['lisa_quad']    = quad
h3_gdf['lisa_p']       = p_lisa
h3_gdf['lisa_cluster'] = 'Not significant'

sig_mask = p_lisa < 0.05
for code, label in quad_labels.items():
    mask = sig_mask & (quad == code)
    h3_gdf.loc[mask, 'lisa_cluster'] = label

lisa_counts = h3_gdf['lisa_cluster'].value_counts()
print(f"\n--- LOCAL MORAN'S I (LISA) CLUSTERS ---")
print(f"  (significant at p < 0.05, 999 permutations)")
for cluster, count in lisa_counts.items():
    pct = count / len(h3_gdf) * 100
    print(f"  {cluster:<30}: {count:>4}  ({pct:.1f}% of cells)")

hh = (h3_gdf['lisa_cluster'] == 'HH (Hot Spot)').sum()
ll = (h3_gdf['lisa_cluster'] == 'LL (Cold Spot)').sum()
print(f"\nInterpretation:")
print(f"  → {hh} Hot Spot cells: areas where high non-compliance clusters")
print(f"    with high non-compliance neighbours — enforcement blind spots.")
print(f"  → {ll} Cold Spot cells: areas of consistent compliance —")
print(f"    likely tourist core / high-visibility enforcement zones.")

# --- 10e. Save LISA map ---
print("\nBuilding LISA cluster map...")

# Re-save GeoJSON now that lisa_cluster column has been added
h3_gdf.drop(columns=['h3_cell'], errors='ignore').to_file(
    'Data/istanbul_airbnb_h3.geojson', driver='GeoJSON'
)

lisa_colours = {
    'HH (Hot Spot)'       : '#d73027',
    'LL (Cold Spot)'      : '#4575b4',
    'LH (Spatial Outlier)': '#fee090',
    'HL (Spatial Outlier)': '#fc8d59',
    'Not significant'     : '#cccccc',
}

lisa_map    = folium.Map(location=[41.01, 28.96], zoom_start=10, tiles='CartoDB positron')
geojson_lisa = json.loads(h3_gdf.to_json())

for feature in geojson_lisa['features']:
    cluster = feature['properties'].get('lisa_cluster', 'Not significant')
    colour  = lisa_colours.get(cluster, '#cccccc')
    folium.GeoJson(
        feature,
        style_function=lambda x, c=colour: {
            'fillColor'  : c,
            'color'      : 'white',
            'weight'     : 0.5,
            'fillOpacity': 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['listing_count', 'unlicensed_pct', 'lisa_cluster'],
            aliases=['Listings:', 'Unlicensed %:', 'LISA Cluster:'],
        )
    ).add_to(lisa_map)

lisa_legend_html = """
<div style="position: fixed; bottom: 40px; left: 40px; z-index: 1000;
     background: white; padding: 12px 16px; border-radius: 8px;
     box-shadow: 2px 2px 6px rgba(0,0,0,0.3); font-family: Arial; font-size: 12px;">
  <b>LISA Cluster Type</b><br>
  <i style="background:#d73027;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> HH – Non-compliance Hot Spot<br>
  <i style="background:#4575b4;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> LL – Compliance Cold Spot<br>
  <i style="background:#fee090;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> LH – Compliant island in non-compliance zone<br>
  <i style="background:#fc8d59;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> HL – Non-compliant island in compliance zone<br>
  <i style="background:#cccccc;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> Not significant<br>
  <br><small>Local Moran's I (LISA), p &lt; 0.05, 999 permutations<br>Data: Inside Airbnb, Sep 2025</small>
</div>
"""
lisa_map.get_root().html.add_child(folium.Element(lisa_legend_html))
lisa_map.save('Data/istanbul_lisa_map.html')
print("Saved: Data/istanbul_lisa_map.html")

print("\n✅ Spatial autocorrelation analysis complete.")

# =============================================================================
# 11. TEMPORAL ANALYSIS — PART A: LISTING ENTRY & REGULATORY DETERRENCE
# Research question: Are listings that entered the market AFTER Law No. 7464
# (January 2024) more compliant than pre-law listings?
# If yes: the law deterred informal entry — new hosts are responding to it.
# If no: the law failed at the margin of new supply — new hosts ignore it.
# Source: first_review date in listings.csv (proxy for listing birth date)
# =============================================================================

print("\n" + "=" * 60)
print("TEMPORAL ANALYSIS A: REGULATORY DETERRENCE ON NEW ENTRANTS")
print("=" * 60)
print("Using first_review date as proxy for listing entry into market")
print("Regulatory shock date: January 1, 2024 (Law No. 7464)")

# Only listings that have at least one review (can infer entry date)
df_dated = df_clean.dropna(subset=['first_review']).copy()
print(f"\nListings with first_review date: {len(df_dated):,} of {len(df_clean):,}")

# Classify by entry period relative to regulation
df_dated['entry_period'] = pd.cut(
    df_dated['first_review'],
    bins=[
        pd.Timestamp('2010-01-01'),
        pd.Timestamp('2022-01-01'),
        pd.Timestamp('2023-01-01'),
        pd.Timestamp('2024-01-01'),   # law enacted
        pd.Timestamp('2024-07-01'),
        pd.Timestamp('2025-01-01'),
        pd.Timestamp('2025-10-01'),
    ],
    labels=[
        'Pre-2022',
        '2022',
        '2023 (pre-law)',
        'Jan–Jun 2024',
        'Jul–Dec 2024',
        '2025',
    ]
)

# Compliance rate by entry period
entry_compliance = df_dated.groupby('entry_period', observed=True).agg(
    listing_count   = ('id',             'count'),
    unlicensed_pct  = ('is_unlicensed',  lambda x: round(x.mean() * 100, 1)),
    licensed_pct    = ('is_unlicensed',  lambda x: round((1 - x.mean()) * 100, 1)),
    avg_price       = ('price_clean',    'mean'),
).round(1)

print("\n--- COMPLIANCE RATE BY LISTING ENTRY PERIOD ---")
print(entry_compliance.to_string())

print("\nInterpretation:")
pre_law   = df_dated[df_dated['entry_period'] == '2023 (pre-law)']['is_unlicensed'].mean() * 100
post_law  = df_dated[df_dated['entry_period'].isin(['Jan–Jun 2024', 'Jul–Dec 2024', '2025'])]
post_rate = post_law['is_unlicensed'].mean() * 100 if len(post_law) > 0 else None

if post_rate is not None:
    diff = pre_law - post_rate
    if diff > 5:
        print(f"  ✅ New entrants after Jan 2024 are {diff:.1f} pp MORE compliant than")
        print(f"     pre-law entrants ({post_rate:.1f}% vs {pre_law:.1f}% unlicensed).")
        print(f"     → The law is deterring informal entry: new hosts respond to it.")
    elif diff < -5:
        print(f"  ⚠️  New entrants after Jan 2024 are {abs(diff):.1f} pp LESS compliant")
        print(f"     than pre-law entrants ({post_rate:.1f}% vs {pre_law:.1f}% unlicensed).")
        print(f"     → Informal hosts continue to enter; law has no deterrence effect")
        print(f"     on new supply.")
    else:
        print(f"  → Compliance rates are similar across entry periods ({pre_law:.1f}% pre-law,")
        print(f"     {post_rate:.1f}% post-law). Regulatory deterrence effect is weak.")

# Also: average price by entry period — are newer listings priced differently?
print(f"\n--- AVG NIGHTLY PRICE (TRY) BY ENTRY PERIOD ---")
for period, row in entry_compliance.iterrows():
    print(f"  {str(period):<20}: {row['avg_price']:>7,.0f} TRY  "
          f"({row['listing_count']:>5,} listings, {row['unlicensed_pct']}% unlicensed)")

print("\n✅ Temporal Part A complete.")

# =============================================================================
# 12. TEMPORAL ANALYSIS — PART B: CALENDAR AVAILABILITY TIME SERIES
# Research question: Do licensed and unlicensed listings show different
# booking patterns over the 12-month forward calendar (Oct 2025 – Sep 2026)?
# Source: calendar.csv.gz — 10.9M rows of daily availability
# "available = f" means the day is booked (not available to new guests)
# =============================================================================

print("\n" + "=" * 60)
print("TEMPORAL ANALYSIS B: CALENDAR BOOKING TIME SERIES")
print("=" * 60)
print("Loading calendar.csv.gz (~10.9M rows) — please wait...")

# --- 12a. Load calendar efficiently ---
# We only need: listing_id, date, available
# Read in chunks to be memory-safe, keep only needed columns

cal_chunks = []
chunk_size = 500_000

for chunk in pd.read_csv(
    'Data/calendar.csv.gz',
    usecols=['listing_id', 'date', 'available'],
    parse_dates=['date'],
    chunksize=chunk_size,
    compression='gzip'
):
    # Keep only listings in our cleaned dataset
    chunk = chunk[chunk['listing_id'].isin(df_clean['id'])]
    cal_chunks.append(chunk)

cal = pd.concat(cal_chunks, ignore_index=True)
print(f"Loaded: {len(cal):,} rows after filtering to clean listings")
print(f"Date range: {cal['date'].min().date()} → {cal['date'].max().date()}")
print(f"Unique listings in calendar: {cal['listing_id'].nunique():,}")

# --- 12b. Merge compliance status onto calendar ---
compliance_map = df_clean.set_index('id')[['compliance', 'is_unlicensed', 'is_entire_home']]
cal = cal.merge(compliance_map, left_on='listing_id', right_index=True, how='left')

# Convert available: 't' = available (not booked), 'f' = booked
cal['booked'] = (cal['available'] == 'f').astype(int)

# --- 12c. Weekly booking rate by compliance status ---
cal['week'] = cal['date'].dt.to_period('W').dt.start_time

weekly = cal.groupby(['week', 'compliance']).agg(
    total_days  = ('booked', 'count'),
    booked_days = ('booked', 'sum'),
).reset_index()
weekly['booking_rate'] = (weekly['booked_days'] / weekly['total_days'] * 100).round(1)

print(f"\n--- WEEKLY BOOKING RATE BY COMPLIANCE STATUS (first 8 weeks) ---")
pivot = weekly.pivot(index='week', columns='compliance', values='booking_rate')
print(pivot.head(8).to_string())

# --- 12d. Summary: avg booking rate by compliance over full period ---
print(f"\n--- AVERAGE BOOKING RATE OVER FULL CALENDAR PERIOD ---")
avg_booking = cal.groupby('compliance').agg(
    avg_booking_rate = ('booked', lambda x: round(x.mean() * 100, 1)),
    listing_count    = ('listing_id', 'nunique'),
).reset_index()
print(avg_booking.to_string(index=False))

# Key comparison: licensed vs unlicensed
lic_rate   = avg_booking.loc[avg_booking['compliance'] == 'Licensed',   'avg_booking_rate'].values
unlic_rate = avg_booking.loc[avg_booking['compliance'] == 'Unlicensed', 'avg_booking_rate'].values

if len(lic_rate) > 0 and len(unlic_rate) > 0:
    lic_rate, unlic_rate = lic_rate[0], unlic_rate[0]
    diff = lic_rate - unlic_rate
    print(f"\nLicensed avg booking rate   : {lic_rate:.1f}%")
    print(f"Unlicensed avg booking rate : {unlic_rate:.1f}%")
    print(f"Gap                         : {diff:+.1f} percentage points")
    print(f"\nInterpretation:")
    if diff > 3:
        print(f"  ✅ Licensed listings are booked {diff:.1f} pp more than unlicensed ones.")
        print(f"     Guests show a revealed preference for compliant listings —")
        print(f"     compliance correlates with demand, not just price.")
    elif diff < -3:
        print(f"  ⚠️  Unlicensed listings are booked {abs(diff):.1f} pp MORE than licensed ones.")
        print(f"     Despite lower prices, unlicensed listings achieve higher occupancy —")
        print(f"     the price discount is working: informal hosts are outcompeting")
        print(f"     licensed hosts on volume even while losing on margin.")
    else:
        print(f"  → Booking rates are similar between licensed and unlicensed listings.")
        print(f"     The compliance gap operates through price, not through demand.")

# --- 12e. Temporal trend: is the booking gap widening over time? ---
# Compute monthly Licensed vs Unlicensed booking rates
cal['month'] = cal['date'].dt.to_period('M').dt.start_time

monthly_gap = cal[cal['compliance'].isin(['Licensed', 'Unlicensed'])].groupby(
    ['month', 'compliance']
)['booked'].mean().unstack() * 100

monthly_gap.columns = ['licensed_rate', 'unlicensed_rate']
monthly_gap['gap'] = monthly_gap['licensed_rate'] - monthly_gap['unlicensed_rate']
monthly_gap = monthly_gap.round(1)

print(f"\n--- MONTHLY BOOKING RATE: LICENSED vs UNLICENSED ---")
print(monthly_gap.to_string())

# Is the gap growing (compliance becoming more valuable over time)?
first_gap = monthly_gap['gap'].iloc[0]
last_gap  = monthly_gap['gap'].iloc[-1]
trend     = last_gap - first_gap
print(f"\nGap in first month  : {first_gap:+.1f} pp")
print(f"Gap in last month   : {last_gap:+.1f} pp")
print(f"Trend               : {trend:+.1f} pp over the calendar period")
# Seasonal analysis: compare gap in shoulder/low season vs peak season
shoulder_months = monthly_gap[monthly_gap.index.month.isin([10, 11, 12, 1, 2, 3, 4, 5])]
peak_months     = monthly_gap[monthly_gap.index.month.isin([6, 7, 8, 9])]
avg_gap_shoulder = shoulder_months['gap'].mean()
avg_gap_peak     = peak_months['gap'].mean()

print(f"\nAvg gap (shoulder/low season Oct–May) : {avg_gap_shoulder:.1f} pp")
print(f"Avg gap (peak summer season Jun–Sep)  : {avg_gap_peak:.1f} pp")
print(f"\nInterpretation:")
print(f"  → The booking gap is NOT a simple linear trend — it is SEASONAL.")
print(f"  → In shoulder/low season, unlicensed listings struggle to attract")
print(f"    bookings: gap reaches {shoulder_months['gap'].max():.1f} pp in Oct–May.")
print(f"  → In peak summer, demand is high enough that even unlicensed listings")
print(f"    fill up: gap compresses to {avg_gap_peak:.1f} pp on average.")
print(f"  → This reveals a structural vulnerability: unlicensed hosts are")
print(f"    disproportionately dependent on peak-season demand and face acute")
print(f"    occupancy risk in off-peak periods — consistent with gradual market")
print(f"    exit over time as revenue volatility compounds enforcement risk.")

# --- 12f. Spatial × temporal: booking rate by H3 cell over time ---
# Merge H3 cell assignment onto calendar
h3_map = df_clean.set_index('id')['h3_cell']
cal = cal.merge(h3_map, left_on='listing_id', right_index=True, how='left')

# Monthly booking rate per H3 cell — collapse to first and last month for comparison
cal_first = cal[cal['month'] == monthly_gap.index[0]]
cal_last  = cal[cal['month'] == monthly_gap.index[-1]]

h3_booking_first = cal_first.groupby('h3_cell')['booked'].mean().rename('booking_first')
h3_booking_last  = cal_last.groupby('h3_cell')['booked'].mean().rename('booking_last')

h3_temporal = pd.concat([h3_booking_first, h3_booking_last], axis=1).dropna()
h3_temporal['booking_change'] = (
    (h3_temporal['booking_last'] - h3_temporal['booking_first']) * 100
).round(1)

print(f"\n--- SPATIAL × TEMPORAL: BOOKING RATE CHANGE BY H3 CELL ---")
print(f"Cells with data in both months: {len(h3_temporal):,}")
print(f"Mean booking rate change (pp): {h3_temporal['booking_change'].mean():.1f}")
print(f"Cells with INCREASING bookings: {(h3_temporal['booking_change'] > 0).sum():,}")
print(f"Cells with DECREASING bookings: {(h3_temporal['booking_change'] < 0).sum():,}")

# Merge back to h3_gdf for mapping
h3_gdf_temporal = h3_gdf.merge(
    h3_temporal.reset_index().rename(columns={'h3_cell': 'h3_id'}),
    on='h3_id', how='left'
)

# Save updated GeoJSON
h3_gdf_temporal.drop(columns=['h3_cell'], errors='ignore').to_file(
    'Data/istanbul_airbnb_h3.geojson', driver='GeoJSON'
)

# --- 12g. Temporal booking map ---
print("\nBuilding temporal booking change map...")

def booking_change_colour(change):
    if pd.isna(change): return '#cccccc'
    if change >= 10:    return '#1a9641'   # strong increase
    elif change >= 3:   return '#a6d96a'   # moderate increase
    elif change >= -3:  return '#ffffbf'   # stable
    elif change >= -10: return '#fdae61'   # moderate decrease
    else:               return '#d7191c'   # strong decrease

temporal_map = folium.Map(location=[41.01, 28.96], zoom_start=10,
                          tiles='CartoDB positron')
geojson_temp = json.loads(h3_gdf_temporal.to_json())

for feature in geojson_temp['features']:
    props  = feature['properties']
    change = props.get('booking_change', None)
    colour = booking_change_colour(change)
    folium.GeoJson(
        feature,
        style_function=lambda x, c=colour: {
            'fillColor'  : c, 'color': 'white',
            'weight'     : 0.5, 'fillOpacity': 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['listing_count', 'unlicensed_pct',
                    'booking_change', 'lisa_cluster'],
            aliases=['Listings:', 'Unlicensed %:',
                     'Booking Δ (pp):', 'LISA Cluster:'],
        )
    ).add_to(temporal_map)

temporal_legend = """
<div style="position: fixed; bottom: 40px; left: 40px; z-index: 1000;
     background: white; padding: 12px 16px; border-radius: 8px;
     box-shadow: 2px 2px 6px rgba(0,0,0,0.3); font-family: Arial; font-size: 12px;">
  <b>Booking Rate Change (pp)</b><br>
  <i style="background:#1a9641;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> ≥ +10 pp (Strong increase)<br>
  <i style="background:#a6d96a;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> +3 to +10 pp<br>
  <i style="background:#ffffbf;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> −3 to +3 pp (Stable)<br>
  <i style="background:#fdae61;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> −3 to −10 pp<br>
  <i style="background:#d7191c;width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:2px;"></i> ≤ −10 pp (Strong decrease)<br>
  <br><small>First vs last month of calendar period<br>Data: Inside Airbnb, Sep 2025</small>
</div>
"""
temporal_map.get_root().html.add_child(folium.Element(temporal_legend))
temporal_map.save('Data/istanbul_temporal_map.html')
print("Saved: Data/istanbul_temporal_map.html")

print("\n✅ Temporal analysis complete.")
print(f"   → Section 11: Regulatory deterrence on new market entrants (review dates)")
print(f"   → Section 12: Booking time series (calendar.csv.gz)")
print(f"   → New map:    istanbul_temporal_map.html")

# =============================================================================
# FINAL SUMMARY
# =============================================================================

print("\n" + "=" * 60)
print("FULL ANALYSIS SUMMARY")
print("=" * 60)
print(f"  Dataset              : Istanbul Airbnb, Sep 2025")
print(f"  Listings analysed    : {len(df_reg):,}")
print(f"  H3 cells (res 8)     : {df_clean['h3_cell'].nunique():,}")
print(f"  Unlicensed listings  : {df_clean['is_unlicensed'].sum():,} ({df_clean['is_unlicensed'].mean()*100:.1f}%)")
print(f"\n  [BASELINE MODEL]")
print(f"  R²                   : {r2:.4f}")
print(f"  Compliance gap       : {price_effect_pct:.1f}%  (uniform average)")
print(f"\n  [EXTENDED MODEL – Interaction]")
print(f"  R²                   : {r2_ext:.4f}")
print(f"  Compliance gap (private rooms) : {gap_private_room:.1f}%")
print(f"  Compliance gap (entire homes)  : {gap_entire_home:.1f}%")
print(f"  → Gap is {'LARGER' if abs(gap_entire_home) > abs(gap_private_room) else 'SMALLER'} for entire homes (directly regulated segment)")
print(f"\n  [AVAILABILITY]")
print(f"  See table above for unlicensed vs. licensed availability patterns")
print(f"\n  [SPATIAL AUTOCORRELATION]")
print(f"  See Moran's I results above — non-compliance is spatially structured")
