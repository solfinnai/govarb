"""Configuration for the Government Procurement Arbitrage Scanner."""

from dataclasses import dataclass, field

# USAspending API
USASPENDING_BASE_URL = "https://api.usaspending.gov/api/v2"
SEARCH_ENDPOINT = f"{USASPENDING_BASE_URL}/search/spending_by_award/"
AWARD_DETAIL_ENDPOINT = f"{USASPENDING_BASE_URL}/awards"

# Rate limiting
REQUEST_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30

# Award type codes: A=BPA, B=Purchase Order, C=Delivery Order, D=Definitive Contract
AWARD_TYPE_CODES = ["A", "B", "C", "D"]

# PSC categories known for COTS overpricing
PSC_CATEGORIES: dict[str, str] = {
    "5935": "Connectors, Electrical",
    "5940": "Lugs, Terminals, and Terminal Strips",
    "5945": "Relays and Solenoids",
    "5961": "Semiconductor Devices and Associated Hardware",
    "5962": "Microcircuits, Electronic",
    "5999": "Electrical and Electronic Components, Misc",
    "6135": "Batteries, Primary",
    "6145": "Wire and Cable, Electrical",
    "7025": "ADP Input/Output and Storage Devices",
    "7035": "ADP Support Equipment",
    "7050": "ADP Components",
}

# Scoring weights
SCORING_WEIGHTS = {
    "single_bidder_bonus": 20,
    "no_set_aside_bonus": 10,
    "cots_designation_bonus": 15,
    "recent_contract_bonus": 10,  # within last 12 months
}

# Markup thresholds for scoring
MARKUP_SCORE_TIERS = [
    (50.0, 100),  # 50x+ markup
    (20.0, 95),
    (10.0, 90),
    (7.0, 75),
    (5.0, 60),
    (3.0, 40),
    (2.0, 20),
    (1.5, 10),
]

# Default filters
DEFAULT_MIN_MARKUP = 5.0
DEFAULT_SCAN_LIMIT = 100
