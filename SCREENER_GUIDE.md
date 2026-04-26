# Trendlyne Screener Export Guide

**Add these columns BEFORE exporting CSVs. More columns = richer dashboard intelligence.**

---

## ENGINE B — DVM Screener (Mom file)
**Screener:** Durability > 55 AND Momentum > 59

### Required Columns (auto-detected):
- Stock Name / NSE Code
- Trendlyne Durability Score
- Trendlyne Momentum Score
- LTP / Current Price

### Add These for Intelligence (click "Add Column" in Trendlyne):
- ROE Annual %
- PE TTM
- Piotroski Score
- Market Capitalization
- 52 Week High
- 52 Week Low
- Sector
- Promoter Holding %
- FII Holding %
- DII Holding %

---

## ENGINE C — Value Screeners (C1, C2 files)

### Screener 1: ROE>15, PE<25, >200DMA, Piotroski>6, MCap>1000
### Screener 2: + D/E<1, Profit Growth YoY>15%

### Add These Extra Columns:
- Market Capitalization
- Debt to Equity
- Profit Growth Annual YoY %
- Revenue QoQ Growth %
- 52 Week High
- 52 Week Low
- Sector
- Promoter Holding %
- ROCE

---

## ENGINE D — Compounder Screeners (D1, D2 files)

### Screener 3: ROE>15, PEG<=1.5, >200DMA, Pio>6, D/E<1, PG YoY>15%, MCap>1000
### Screener 4: ROE>15, PE<25, >200DMA, Pio>6, D/E<1, PG 3Yr>15%, MCap>1000

### Add These Extra Columns:
- PEG TTM
- Market Capitalization
- Debt to Equity
- Profit Growth Annual YoY %
- Revenue QoQ Growth %
- 52 Week High
- 52 Week Low
- Sector
- Promoter Holding %
- ROCE

---

## File Naming Convention

| Engine | Prefix | Example |
|--------|--------|---------|
| B (Momentum) | `Mom` | Mom 1_April 26, 2026.csv |
| C Screener 1 | `C1` | C1 Value_April 26, 2026.csv |
| C Screener 2 | `C2` | C2 Value_April 26, 2026.csv |
| D Screener 3 | `D1` | D1 Compound_April 26, 2026.csv |
| D Screener 4 | `D2` | D2 Compound_April 26, 2026.csv |

Upload all files to GitHub repo → `data/` folder → then press "Load from GitHub" on dashboard.
