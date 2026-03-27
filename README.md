# GovArb Scanner

Government procurement arbitrage scanner that identifies overpriced COTS (Commercial Off-The-Shelf) items in federal contracts by comparing USAspending.gov award data against estimated commercial prices.

## How It Works

1. **Fetch** — Queries the USAspending.gov API for recent contracts in known COTS-heavy PSC (Product Service Code) categories: connectors, batteries, semiconductors, IT equipment, etc.
2. **Price** — Matches contract descriptions against an internal lookup table of commercial price ranges (sourced from DigiKey, Mouser, CDW-G, and OEM catalogs).
3. **Analyze** — Scores each contract on markup ratio, competition level (single-bidder vs. competed), COTS designation, set-aside status, and recency.
4. **Report** — Displays ranked opportunities in the terminal and optionally writes a detailed Markdown report.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Dry run with realistic sample data
python scanner.py --dry-run

# Scan specific PSC categories
python scanner.py --categories 5935 6135 5962

# High-markup scan with limited results
python scanner.py --min-markup 10 --limit 50

# Save report to file
python scanner.py --dry-run --output report.md
```

### CLI Options

| Option | Default | Description |
|---|---|---|
| `--categories PSC [PSC ...]` | All configured | PSC codes to scan |
| `--min-markup N` | 5 | Minimum markup ratio to include |
| `--limit N` | 100 | Max contracts to fetch from API |
| `--output FILE` | — | Write markdown report to FILE |
| `--dry-run` | — | Use sample data instead of live API |

### Available PSC Categories

| Code | Description |
|---|---|
| 5935 | Connectors, Electrical |
| 5940 | Lugs, Terminals, and Terminal Strips |
| 5945 | Relays and Solenoids |
| 5961 | Semiconductor Devices |
| 5962 | Microcircuits, Electronic |
| 5999 | Electrical/Electronic Components, Misc |
| 6135 | Batteries, Primary |
| 6145 | Wire and Cable, Electrical |
| 7025 | ADP Input/Output and Storage Devices |
| 7035 | ADP Support Equipment |
| 7050 | ADP Components |

## Example Output

```
┌──────────────────────────────────────────────────────────────────────┐
│ GovArb Scanner Results [DRY RUN]                                     │
│ Found 12 opportunities | Total addressable value: $8.52M             │
└──────────────────────────────────────────────────────────────────────┘
   # │ Contract ID          │ Description                  │ Award Amt │ …
   1 │ W56HZV-25-P-3241     │ LUG,TERMINAL - MS25036-153…  │   $12.5K  │ …
   2 │ N68335-26-C-0039     │ SEMICONDUCTOR DEVICE,TRANS…  │   $89.1K  │ …
   3 │ N00024-25-C-6218     │ CONNECTOR,RECEPTACLE - D38…  │  $534.0K  │ …
```

## Scoring

Each opportunity is scored 0–100 based on:

- **Markup ratio** (0–100 base): Higher government-to-commercial price ratio = higher score
- **Single bidder** (+20): No competition suggests pricing power
- **No set-aside** (+10): Unrestricted contracts have less competition pressure
- **COTS designation** (+15): Item is explicitly commercial, making comparison valid
- **Recent contract** (+10): Awarded within last 12 months, still actionable

## Project Structure

```
├── scanner.py        # CLI entry point
├── usaspending.py    # USAspending.gov API client
├── pricing.py        # Commercial price lookup engine
├── analyzer.py       # Opportunity scoring
├── report.py         # Terminal + markdown report generation
├── config.py         # Configuration and constants
└── requirements.txt  # Python dependencies
```

## Disclaimer

This tool is for research and analysis purposes. Price estimates are approximate and based on publicly available commercial pricing data. Always verify pricing independently before making procurement decisions.
