# 🏰 Indian Equity Moat Screener

A Python-based algorithmic screening model that identifies NSE-listed companies with **durable competitive advantages** (economic moats) — companies likely to compound wealth over many years.

---

## 🎯 What It Finds

Companies that exhibit:
- **Consistently high ROCE** (>20%) — the ultimate moat signal
- **Stable, high gross margins** — pricing power over customers/suppliers
- **FCF > Net Income** — real cash generation, not accounting profits
- **Low/No Debt** — financial fortress, no vulnerability to rate cycles
- **Sustained revenue growth** — demand leadership in their domain
- **Expanding operating margins** — increasing competitive advantage over time

---

## 🏗️ Architecture

```
moats/
├── screener.py            # 🚀 Main entry point (run this)
├── config.py              # Universe (~150 stocks), thresholds & weights
├── data_fetcher.py        # yfinance data layer with caching
├── metrics_calculator.py  # Computes all financial ratios
├── moat_scorer.py         # Scores companies 0–100
├── report_generator.py    # Console, Excel & HTML output
├── requirements.txt       # Python dependencies
└── output/                # Generated reports (auto-created)
```

---

## 📊 Scoring Model (100 Points)

| Dimension | Points | Key Metrics |
|-----------|--------|-------------|
| 🏰 **Moat** | 40 | ROCE avg & consistency, Gross Margin, FCF Conversion |
| 💎 **Quality** | 25 | Debt/Equity, CFO/PAT ratio, Interest Coverage |
| 📈 **Growth** | 25 | Revenue CAGR (3yr/5yr), EPS CAGR |
| ⚙️ **Efficiency** | 10 | Asset Turnover, Operating Leverage |

### Moat Labels
| Score | Label |
|-------|-------|
| ≥ 70 | 🏰 Strong Moat |
| ≥ 50 | 🌱 Emerging Moat |
| ≥ 35 | 👀 Watchlist |
| < 35  | ❌ No Moat |

---

## 🚀 Usage

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Screener

```bash
# Screen the full universe (~150 NSE stocks)
python screener.py

# Screen a specific sector
python screener.py --sector "Information Technology"
python screener.py --sector "Healthcare & Pharma"
python screener.py --sector "Consumer Staples"

# Screen custom tickers
python screener.py --tickers TCS.NS INFY.NS PIDILITIND.NS EICHERMOT.NS

# Show top 10 only, with minimum score 50
python screener.py --top 10 --min-score 50

# Disable hard filters (include all companies regardless of ROCE/Debt)
python screener.py --no-hard-filter

# Available sectors:
#   Financials, Information Technology, Consumer Staples,
#   Consumer Discretionary, Healthcare & Pharma, Automobiles,
#   Capital Goods & Industrials, Chemicals & Materials,
#   Specialty & Niche, Energy & Utilities, Telecom, Cement,
#   Conglomerates & Infra
```

---

## 📂 Output Files

All saved to `output/` directory:
- **`moat_screen_YYYYMMDD_HHMM.xlsx`** — Excel workbook with all metrics + color coding
- **`moat_screen_YYYYMMDD_HHMM.html`** — Dark-themed HTML report, open in browser
- **Console** — Rich formatted table with top results

---

## 📐 Key Metrics Explained (India Context)

### ROCE (Return on Capital Employed)
> EBIT / (Total Equity + Total Debt)

**Why it matters**: The single best indicator of a moat. Companies like HDFC Bank, Asian Paints, and Page Industries maintained ROCE >25% for 10+ years — this is what separates true compounders from pretenders.

- **≥25%**: Exceptional moat (full points)
- **18-25%**: Good moat
- **12-18%**: Entry level
- **<12%**: Filtered out

### Gross Margin Consistency
High and **stable** gross margins indicate:
1. Pricing power over customers
2. Control over input costs (or ability to pass them through)
3. Differentiated product/service

**Indian Examples**: Nestlé India (>55%), HDFC Life (>70%), Page Industries (>55%)

### FCF Conversion (FCF / Net Income)
**Why it matters**: Indian companies often manipulate working capital to show paper profits. FCF > Net Income = real earnings, hard to fake.

- **≥90%**: Excellent (earns in cash what it reports)
- **70-90%**: Good
- **<50%**: Investigate further

### CFO/PAT Ratio
Operating Cash Flow / Net Profit. Should ideally be **>1.0** for quality businesses.

### Debt/Equity
- **<0.1**: Virtually debt-free (net cash bonus awarded)
- **<0.5**: Conservative
- **>1.5**: Flagged as risky; filtered by default at >3.0

---

## ⚠️ Limitations & Caveats

1. **Data quality**: yfinance may have inconsistencies for some Indian stocks
2. **No promoter holding data**: Requires BSE/NSE API for this Indian-specific metric
3. **No pledging data**: Important signal in India — check manually on BSE
4. **Sector context**: Thresholds are generalised; financials (banks/NBFCs) should be evaluated differently (use ROE/NIM instead of ROCE)
5. **Historical data**: yfinance typically provides 4-5 years of annual data for Indian stocks
6. **Not financial advice**: Research tool only. Always do your own due diligence.

---

## 🔬 Supplementary Data Sources (Manual)

| Source | What to Check |
|--------|--------------|
| [Screener.in](https://www.screener.in) | Promoter holding, pledging, Piotroski score |
| [BSE India](https://www.bseindia.com) | Shareholding pattern, bulk deals |
| [NSE India](https://www.nseindia.com) | FII/DII activity, circuit limits |
| [Tijori Finance](https://tijorifinance.com) | Concall transcripts, management commentary |
| [Trendlyne](https://trendlyne.com) | Analyst consensus, earnings beat/miss |
| [ValueResearchOnline](https://www.valueresearchonline.com) | Mutual fund holdings |

---

## 📚 Framework References

- **"The Little Book That Builds Wealth"** — Pat Dorsey
- **Morningstar Economic Moat Framework** — moat categories
- **"Coffee Can Investing"** — Saurabh Mukherjea (India-specific)
- **"The Unusual Billionaires"** — Saurabh Mukherjea (Indian compounders)

---

> 💡 **Pro Tip**: Run the screener quarterly. Compare how companies move in/out of the Strong Moat category — deteriorating scores are early warning signs before the market notices.
