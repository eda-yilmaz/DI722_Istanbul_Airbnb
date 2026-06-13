# Spatio-Temporal Impact of STR Regulation on Airbnb in Istanbul

**DI 722 – Spatio-Temporal Data Mining | METU**  
**Author:** Eda Yılmaz  
**Data:** Inside Airbnb – Istanbul (Scraped: September 2025)

---

## 1. Research Question

Does Turkey's short-term rental regulation (Law No. 7464, January 2024) produce a measurable spatial and pricing footprint in the Istanbul Airbnb market — and if so, where is the effect concentrated?

The law requires hosts renting for fewer than 100 consecutive nights to obtain a permit from the Ministry of Culture and Tourism. Non-compliance (operating without a permit) is the study's key variable.

---

## 2. Data

| Source | File | Description |
|--------|------|-------------|
| Inside Airbnb | `Data/listings.csv` | ~27,000 listings scraped Sep 2025; includes `license` field |
| Inside Airbnb | `Data/calendar.csv.gz` | ~10.9M rows; daily availability for each listing |

**License field classification:**

| Category | Meaning |
|----------|---------|
| Licensed | Has a permit number issued under Law No. 7464 |
| Unlicensed | `license` is NaN — no permit recorded |
| Exempt | Legally exempt from permit requirement |
| Non-real estate | Hotels, B&Bs — different legal category |

---

## 3. Spatial Framework

Listings are assigned to **H3 hexagonal cells at Resolution 8** (~0.74 km² per cell), following the DGGS approach recommended for urban STR studies. Istanbul is covered by 1,262 cells; analyses requiring stable estimates use cells with ≥ 5 active listings (311 cells).

Spatial weights are built directly from H3 topology: each cell's six immediate neighbours form a row-standardised weight row, equivalent to Queen contiguity on hexagonal grids. No external spatial libraries (libpysal/esda) are required.

---

## 4. Methodology

### Phase 1 — Baseline Analysis (`Spatial_Project.py`)

**4.1 Data cleaning and H3 assignment**  
Price outliers (top 1%) and listings outside the Istanbul bounding box are removed, leaving ~24,992 cleaned listings. Each listing is assigned to an H3 Resolution-8 cell.

**4.2 Compliance and price maps**  
Interactive folium maps colour each H3 cell by unlicensed rate and average nightly price.

**4.3 Baseline OLS regression**  
Log-price regressed on compliance status, room type, availability, accommodates, and top-10 neighbourhood dummies (drop_first = True; reference = alphabetical first). Key result: the unlicensed price gap.

**4.4 Availability analysis**  
Compares calendar availability (nights/year) and zero-availability rates across compliance categories and room types.

**4.5 Extended OLS with interaction**  
Adds `is_unlicensed × is_entire_home` to test whether the compliance penalty is larger for entire homes — the segment directly targeted by Law No. 7464.

**4.6 Spatial autocorrelation — Global and Local Moran's I (LISA)**  
Global Moran's I for unlicensed rate and price; permutation test (999 draws). LISA clusters (HH/LL/LH/HL) identify spatial hot and cold spots of non-compliance. Sensitivity analysis at k = 1, 2, 3 confirms robustness.

**4.7 Temporal analysis A — Entry cohorts**  
First-review date used as a proxy for listing entry. Cohorts: Pre-2022, 2022, 2023 (pre-law), Jan–Jun 2024, Jul–Dec 2024, 2025. Compares licensed rates across cohorts to assess regulatory deterrence on new entrants.

**4.8 Temporal analysis B — Calendar booking time series**  
Weekly and monthly booking rates for licensed vs. unlicensed listings from `calendar.csv.gz`. Tests whether the compliance gap is seasonal and whether it is growing over the forward calendar period.

---

### Phase 1B — Ghost Listing Sensitivity (`comparison_analysis.py`)

Repeats the three core analyses (Moran's I, OLS price gap, entry cohort) on two samples:
- **Sample A:** all 24,992 cleaned listings
- **Sample B:** active listings only (`number_of_reviews > 0`, ~16,004)

Confirms that ghost listings do not materially distort the headline results.

---

### Phase 2A — Updated OLS: Beşiktaş as Reference Neighbourhood (`advanced_analysis.py`)

Re-runs the baseline OLS with **Beşiktaş as the explicit reference category** (replacing the alphabetically-first default of Bağcılar). Beşiktaş is a high-compliance, central, affluent district, making neighbourhood coefficients interpretable as premiums or discounts relative to a well-licensed baseline.

---

### Phase 2B — Geographically Weighted Regression (`advanced_analysis.py`)

GWR allows each H3 cell to carry its own regression coefficients, revealing where in Istanbul the unlicensed price penalty is strongest or weakest.

| Parameter | Value |
|-----------|-------|
| Library | `mgwr` v2.2 |
| Kernel | Adaptive bisquare |
| Bandwidth selection | AICc criterion (full Sel_BW search) |
| Optimal bandwidth | **101 nearest cells** |
| Cells analysed | 311 (active listings, ≥ 5 per cell) |

Output: per-cell local β for the unlicensed variable, local R², significance flags (|t| > 1.96). Interactive folium map and static matplotlib coefficient map.

---

### Phase 2D — GWR Bandwidth Sensitivity + Variable-Scale Analysis (`mgwr_analysis.py`)

Responds directly to the critique that a single bandwidth of 101 cells is too broad for dense central Istanbul.

**Part A — Bandwidth sensitivity:**  
GWR fitted at bw = 30, 60, and 101 cells. AICc decreases monotonically with broader bandwidth, confirming that 101 cells is the global optimum under the AICc criterion.

| BW | % of cells | Mean R² | AICc |
|----|-----------|---------|------|
| 30 | 9.6% | — | highest |
| 60 | 19.3% | — | intermediate |
| **101** | **32.5%** | **highest** | **lowest ← optimal** |

**Part B — Variable-scale analysis (MGWR approximation):**  
Each predictor is fitted as a univariate GWR across bandwidths [20, 30, …, 200] to find its intrinsic spatial scale. This approximates the first iteration of the MGWR backfitting algorithm.

| Variable | Univariate BW | GWR BW | Scale |
|----------|--------------|--------|-------|
| `unlicensed_rate` | ≤ 20 cells | 101 | **5× finer** |
| `entire_home_rate` | ≤ 20 cells | 101 | finer |
| `mean_availability` | ≤ 20 cells | 101 | finer |
| `mean_accommodates` | 40 cells | 101 | finer |

**Key result:** The compliance effect (`unlicensed_rate`) prefers a bandwidth of ≤ 20 cells — roughly 5× finer than the global optimum. This validates the professor's critique: non-compliance operates in micro-markets that a 101-cell window smooths out. A full MGWR would assign ~20 cells to this variable while allowing control variables to use broader bandwidths.

---

## 5. Key Findings

**Non-compliance rate:** ~38% of cleaned listings are unlicensed (no permit recorded as of Sep 2025).

**Price gap (OLS):** Unlicensed listings are approximately −25% cheaper than licensed ones, controlling for room type, availability, neighbourhood, and accommodates.

**Spatial structure:** Global Moran's I = 0.185 (p = 0.001) for unlicensed rate. Non-compliance is significantly clustered — enforcement must be spatially targeted.

**Regulatory deterrence:** The 2025 cohort shows 3.9% unlicensed — far lower than pre-law cohorts. However, cross-sectional identification limits causal interpretation for earlier cohorts (see §6).

**GWR spatial heterogeneity:** The unlicensed price penalty is concentrated in specific neighbourhoods. Mean local R² exceeds the global OLS R², confirming that the effect is spatially varying.

**Bandwidth sensitivity:** AICc confirms bw = 101 as the global optimum. Variable-scale analysis reveals that the compliance effect is far more localised than the control variables, motivating a full MGWR extension.

---

## 6. Methodological Notes

### 6.1 Cohort classification limitation

License status is observed at a **single point in time** (September 2025). For pre-2024 cohorts, a listing classified as "Unlicensed" may have:
- (a) always been unlicensed,
- (b) held a permit that has since lapsed, or
- (c) obtained a permit after Law No. 7464 and subsequently let it expire.

The most defensible claim about regulatory compliance behaviour applies to the **2025 cohort** (3.9% unlicensed), where the cross-sectional observation coincides closely with market entry. For earlier cohorts, unlicensed rates should be interpreted as the **stock of listings without a valid permit in September 2025**, not as the share that chose to enter without a permit.

This limitation would be resolved by a difference-in-differences design using historical Inside Airbnb scrapes from 2023–2024.

### 6.2 Ghost listing sensitivity

Results are robust to the exclusion of listings with no reviews (`number_of_reviews = 0`). The OLS price gap changes from −25.1% (all listings) to −22.1% (active only); Moran's I moves from 0.185 to 0.184. Findings are not driven by ghost listings.

### 6.3 GWR bandwidth

The AICc-optimal bandwidth of 101 cells reflects a global trade-off across all five model variables. Variable-scale analysis shows that the compliance effect alone would prefer ≤ 20 cells. A full MGWR implementation (not yet feasible in this compute environment due to the ~30-minute backfitting search) would formally quantify this scale difference.

---

## 7. Repository Structure

```
Project/
├── Data/
│   ├── listings.csv                    — Inside Airbnb listings (Sep 2025)
│   ├── calendar.csv.gz                 — Daily availability calendar
│   ├── istanbul_airbnb_h3.geojson      — H3 hexagon polygons with stats + LISA
│   ├── fig_sample_comparison.png       — Ghost listing sensitivity chart
│   ├── fig_gwr_coefficients.png        — GWR local coefficient map
│   ├── fig_mgwr_comparison.png         — Bandwidth sensitivity comparison map
│   ├── mgwr_summary.csv                — Per-cell coefficients at bw=30/60/101
│   ├── mgwr_bandwidths.txt             — Variable-scale analysis results
│   ├── istanbul_compliance_map.html    — Interactive compliance map
│   ├── istanbul_price_map.html         — Interactive price map
│   ├── istanbul_lisa_map.html          — Interactive LISA cluster map
│   ├── istanbul_temporal_map.html      — Booking rate change map
│   ├── istanbul_gwr_map.html           — Interactive GWR coefficient map
│   └── istanbul_mgwr_map.html          — Interactive bandwidth sensitivity map
│
├── Special_Final.py                    — Single merged script (presentation version)
├── Spatial_Project_Final.py            — Full merged script (all analyses)
├── Spatial_Project.py                  — Phase 1 original script
├── comparison_analysis.py              — Ghost listing sensitivity
├── advanced_analysis.py                — GWR + panel regression
├── mgwr_analysis.py                    — Bandwidth sensitivity + variable-scale
└── README.md                           — This file
```

---

## 8. How to Run

```bash
# Install dependencies
pip install pandas numpy h3 geopandas shapely folium scikit-learn mgwr matplotlib joblib

# Run the presentation-version script (no panel regression)
cd Project
python Special_Final.py

# Or run the full analysis script
python Spatial_Project_Final.py
```

**Runtime notes:**
- Data loading and cleaning: ~10 seconds
- LISA (999 permutations): ~30 seconds
- GWR fit (bw=101, threading backend): ~2 seconds per fit
- Bandwidth sensitivity (3 fits): ~6 seconds
- Variable-scale analysis (48 univariate fits): ~30–40 seconds
- Calendar loading from `calendar.csv.gz`: ~30 seconds

The script sets `joblib.parallel_backend('threading', n_jobs=2)` at import time to avoid semaphore conflicts with the `mgwr` library in constrained environments.

---

## 9. References

- Fotheringham, A. S., Brunsdon, C., & Charlton, M. (2002). *Geographically weighted regression: The analysis of spatially varying relationships.* Wiley.
- Fotheringham, A. S., Yang, W., & Kang, W. (2017). Multiscale geographically weighted regression. *Annals of the American Association of Geographers, 107*(6), 1247–1265.
- Bivand, R., & Wong, D. W. S. (2018). Comparing implementations of global and local indicators of spatial association. *TEST, 27*(3), 716–748.
- Uber H3 Documentation. Resolution table. https://h3geo.org/docs/core-library/restable/
- Inside Airbnb. Istanbul dataset, September 2025. http://insideairbnb.com
- Republic of Turkey. Law No. 7464 on the Regulation of Short-Term Rentals. *Official Gazette*, January 2024.
