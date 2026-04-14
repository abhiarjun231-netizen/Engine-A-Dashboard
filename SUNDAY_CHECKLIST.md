# Sunday Morning Engine A Update Checklist

**Time required:** ~2 minutes
**Frequency:** Every Sunday before scoring run
**Goal:** Update `manual_inputs.json` with this week's values from Trendlyne

---

## Weekly updates (every Sunday)

### 1. Nifty 50 PE Ratio
- **Open:** [Trendlyne Nifty 50](https://trendlyne.com/equity/Nifty-50/)
- **Look for:** Big number in "Nifty 50 PE" card (e.g., `20.9`)
- **Update field:** `nifty_pe.value`

### 2. FII 30-day Net Flow
- **Open:** [Trendlyne FII/DII Activity](https://trendlyne.com/macro-data/fii-dii/latest/snapshot-day/)
- **Look for:** "Last 30 Days" row, "FII Net Purchase/Sales" column
- **Update field:** `fii_30day_net_cr.value` (integer, no commas, e.g. `-106613`)

### 3. DII 30-day Net Flow
- **Same page as above**
- **Look for:** "Last 30 Days" row, "DII Net Purchase/Sales" column
- **Update field:** `dii_30day_net_cr.value` (integer, no commas)

### 4. Nifty 500 Breadth
- **Open:** [Trendlyne Nifty 500 above 200 SMA](https://trendlyne.com/fundamentals/preset-screeners/nifty-500-above-200-sma/)
- **Look for:** "Showing 1 - 25 of N results" at bottom
- **Calculate:** `N / 500 * 100`, e.g., `161/500*100 = 32.2`
- **Update field:** `breadth_pct_above_200dma.value`

### 5. Yield Curve Inverted?
- **Open:** [CCIL Yield Curve](https://www.ccilindia.com/web/ccil/yield-curve)
- **Check:** Is 1-year yield HIGHER than 10-year yield?
- **Update field:** `yield_curve_inverted.value` as `"Yes"` or `"No"`

---

## Rare updates (only when policy changes)

### 6. RBI Stance (6x/year after MPC meeting)
- **Open:** [RBI Monetary Policy](https://www.rbi.org.in/Scripts/AnnualPolicy.aspx)
- **Only update if RBI announced new policy this week**
- **Valid values:** `Accommodative-Cutting`, `Accommodative-Paused`, `Neutral`, `Tightening-Paused`, `Tightening-Hiking`
- **Update field:** `rbi_stance.value`

### 7. CPI Inflation (monthly, around 12th)
- **Open:** [MOSPI CPI](https://www.mospi.gov.in/cpi)
- **Update field:** `cpi_pct.value` (e.g., `5.2`)

### 8. PMI Manufacturing (monthly, 1st of month)
- **Open:** [S&P Global India PMI](https://www.pmi.spglobal.com/Public/Release/PressReleases)
- **Update field:** `pmi_manufacturing.value` (e.g., `56.3`)

---

## After updating

1. Update `_last_updated` field at top of JSON to today's date
2. Commit with message: `Update manual inputs - YYYY-MM-DD`
3. Sunday 9 AM cron picks up new values automatically
4. Check `data/engine_a_score.csv` for your new score
