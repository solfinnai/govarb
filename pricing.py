"""Commercial price estimation engine for government contract items.

Three-layer approach:
1. Part number extraction + known price lookup
2. Category + keyword classification with price ranges
3. Quantity inference from total obligation
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommercialPrice:
    """Estimated commercial price for a government contract item."""
    estimated_price: float        # Best estimate (avg of range)
    price_min: float             # Low end
    price_max: float             # High end
    confidence: float            # 0-1
    source: str                  # 'part_number', 'category_keyword', 'category_only', 'no_match'
    category_matched: str        # What we think this item is
    estimated_quantity: int      # Inferred quantity
    unit_price_estimate: float   # Per-unit commercial price


# ─── LAYER 1: Part Number Patterns ──────────────────────────────────────────

PART_NUMBER_PRICES = {
    # Connectors - circular mil-spec
    r'MS3106': (8, 20, 35, 'Circular connector, plug'),
    r'MS3102': (8, 20, 35, 'Circular connector, receptacle'),
    r'MS3108': (10, 25, 40, 'Circular connector, cable clamp'),
    r'MS3126': (5, 15, 30, 'Circular connector, miniature'),
    r'MS27467': (10, 30, 50, 'Circular connector, high-density'),
    r'MS27468': (10, 30, 50, 'Circular connector, high-density'),
    r'MS25036': (0.10, 0.50, 2.0, 'Ring tongue terminal'),
    r'D38999': (15, 50, 150, 'MIL-DTL-38999 connector'),

    # Relays
    r'M39016': (15, 40, 80, 'Military relay'),
    r'M39019': (20, 50, 100, 'Military relay, latching'),
    r'MS27401': (10, 30, 60, 'Relay, electromagnetic'),

    # Semiconductors
    r'JANTXV?2N\d{4}': (2, 5, 15, 'Military transistor'),
    r'JANTXV?1N\d{4}': (1, 3, 8, 'Military diode'),
    r'JANTXV?LM\d{4}': (3, 8, 20, 'Military voltage regulator'),

    # Batteries
    r'BA-5590': (30, 55, 80, 'Lithium primary battery pack'),
    r'BA-5390': (25, 45, 70, 'Lithium primary battery'),
    r'BA-5567': (20, 40, 60, 'Lithium battery'),
    r'BB-2590': (50, 120, 200, 'Lithium-ion rechargeable pack'),

    # Cable/wire
    r'MIL-DTL-17': (1, 3, 8, 'Coax cable per ft'),
    r'W81A/U': (2, 5, 10, 'Coax cable assembly'),
    r'MIL-C-17': (1, 3, 8, 'Coax cable per ft'),

    # Circuit breakers
    r'MS\d+-\d+.*BREAKER': (20, 80, 200, 'Circuit breaker'),
    r'MS3320': (15, 40, 80, 'Circuit breaker, aircraft'),

    # Fuses
    r'F02[A-Z]': (1, 3, 8, 'Military fuse'),
}


# ─── LAYER 2: Category + Keyword Price Ranges ───────────────────────────────

# Format: { 'psc_code': [ (keywords, min, avg, max, description), ... ] }
CATEGORY_PRICES = {
    '5935': [  # Connectors
        (['filter', 'emi', 'rfi', 'filtered'], 50, 125, 200, 'Filtered/EMI connector'),
        (['rf', 'coax', 'bnc', 'sma', 'n-type', 'tnc'], 3, 12, 25, 'RF/Coax connector'),
        (['fiber', 'optical'], 20, 60, 120, 'Fiber optic connector'),
        (['nano', 'micro-d'], 20, 50, 80, 'High-density nano/micro-D connector'),
        (['terminal', 'block', 'strip'], 2, 8, 15, 'Terminal block/strip'),
        (['board', 'pcb', 'header'], 1, 5, 10, 'Board-to-board connector'),
        (['circular', 'plug', 'receptacle', 'ms3', 'd38999'], 5, 20, 50, 'Circular connector'),
        ([], 5, 18, 40, 'Connector, general'),
    ],
    '5940': [  # Lugs, Terminals
        (['ring', 'tongue'], 0.10, 0.50, 2.0, 'Ring terminal'),
        (['spade', 'fork'], 0.10, 0.50, 2.0, 'Spade terminal'),
        (['butt', 'splice'], 0.10, 0.40, 1.50, 'Butt splice'),
        (['strip', 'block'], 5, 15, 30, 'Terminal strip'),
        (['lug'], 0.20, 1.0, 3.0, 'Cable lug'),
        ([], 0.50, 2.0, 5.0, 'Terminal/lug, general'),
    ],
    '5945': [  # Relays
        (['solid state', 'ssr'], 10, 35, 60, 'Solid state relay'),
        (['contactor'], 20, 60, 120, 'Contactor'),
        (['power', 'high current'], 5, 25, 40, 'Power relay'),
        (['latching'], 8, 25, 50, 'Latching relay'),
        (['signal', 'reed'], 3, 12, 20, 'Signal relay'),
        ([], 5, 20, 45, 'Relay, general'),
    ],
    '5961': [  # Semiconductors
        (['mosfet', 'fet', 'power'], 2, 8, 20, 'Power MOSFET'),
        (['transistor', '2n'], 0.50, 3, 10, 'Transistor'),
        (['diode', '1n'], 0.20, 2, 5, 'Diode'),
        (['regulator', 'lm78', 'lm79', 'lm317'], 1, 5, 10, 'Voltage regulator'),
        (['thyristor', 'scr', 'triac'], 2, 8, 20, 'Thyristor/SCR'),
        (['igbt'], 5, 20, 50, 'IGBT'),
        ([], 1, 5, 15, 'Semiconductor, general'),
    ],
    '5962': [  # Microcircuits
        (['fpga', 'cpld', 'programmable'], 50, 200, 500, 'FPGA/CPLD'),
        (['rad', 'radiation', 'space'], 100, 500, 2000, 'Radiation-hardened IC'),
        (['processor', 'microprocessor', 'cpu', 'mcu'], 10, 80, 200, 'Microprocessor/MCU'),
        (['memory', 'ram', 'rom', 'eeprom', 'flash'], 5, 40, 100, 'Memory IC'),
        (['op-amp', 'operational', 'amplifier'], 1, 8, 15, 'Op-amp'),
        (['adc', 'dac', 'converter'], 5, 25, 80, 'ADC/DAC'),
        (['logic', 'gate', 'flip-flop', '74'], 2, 10, 30, 'Logic IC'),
        ([], 5, 30, 100, 'Microcircuit, general'),
    ],
    '6135': [  # Batteries
        (['ba-5590', 'ba5590'], 30, 55, 80, 'BA-5590 lithium primary'),
        (['bb-2590', 'bb2590', 'rechargeable'], 50, 120, 200, 'Rechargeable battery pack'),
        (['lithium', 'li-ion', 'lipo'], 20, 80, 200, 'Lithium battery'),
        (['thermal'], 100, 300, 500, 'Thermal battery'),
        (['alkaline', 'aa', 'aaa', 'd cell'], 1, 3, 5, 'Alkaline battery'),
        (['nicad', 'nimh', 'nickel'], 10, 30, 60, 'NiCad/NiMH battery'),
        ([], 10, 40, 100, 'Battery, general'),
    ],
    '6145': [  # Wire and Cable
        (['assembly', 'harness', 'cable assy'], 10, 50, 100, 'Cable assembly'),
        (['coax', 'coaxial', 'rg-', 'rg/'], 1, 3, 8, 'Coaxial cable (per ft)'),
        (['fiber', 'optical'], 5, 15, 30, 'Fiber optic cable (per m)'),
        (['hookup', 'hook-up', 'wire'], 0.10, 0.30, 0.80, 'Hookup wire (per ft)'),
        (['power', 'heavy', 'gauge'], 2, 8, 20, 'Power cable'),
        ([], 2, 10, 30, 'Wire/cable, general'),
    ],
    '5999': [  # Electrical Components Misc
        (['breaker', 'circuit breaker'], 20, 80, 200, 'Circuit breaker'),
        (['fuse'], 1, 5, 10, 'Fuse'),
        (['switch', 'toggle', 'rocker'], 5, 20, 50, 'Switch'),
        (['potentiometer', 'pot', 'rheostat'], 2, 10, 20, 'Potentiometer'),
        (['transformer'], 10, 50, 150, 'Transformer'),
        (['resistor'], 0.10, 0.50, 2.0, 'Resistor'),
        (['capacitor'], 0.20, 2, 10, 'Capacitor'),
        (['inductor', 'choke', 'coil'], 1, 5, 20, 'Inductor'),
        ([], 5, 25, 60, 'Electrical component, general'),
    ],
    '7025': [  # Computers
        (['server', 'poweredge', 'proliant'], 2000, 5000, 10000, 'Server'),
        (['ruggedized', 'rugged', 'toughbook', 'mil-std-810'], 2000, 3500, 5000, 'Ruggedized computer'),
        (['laptop', 'notebook'], 800, 1500, 3000, 'Laptop'),
        (['tablet'], 500, 1200, 2500, 'Tablet'),
        (['workstation'], 1500, 3000, 6000, 'Workstation'),
        (['desktop'], 600, 1200, 2500, 'Desktop'),
        ([], 1000, 2500, 5000, 'Computer, general'),
    ],
    '7035': [  # IT Equipment
        (['switch', 'cisco', 'catalyst', 'network'], 500, 2000, 5000, 'Network switch'),
        (['router'], 300, 1500, 4000, 'Router'),
        (['firewall'], 500, 2500, 8000, 'Firewall'),
        (['storage', 'san', 'nas', 'disk'], 1000, 4000, 10000, 'Storage system'),
        (['monitor', 'display'], 200, 500, 800, 'Monitor'),
        (['printer'], 200, 600, 2000, 'Printer'),
        (['ups', 'uninterruptible'], 200, 800, 3000, 'UPS'),
        ([], 500, 2000, 5000, 'IT equipment, general'),
    ],
    '7050': [  # Computers (alternate PSC)
        (['server'], 2000, 5000, 10000, 'Server'),
        (['laptop', 'notebook'], 800, 1500, 3000, 'Laptop'),
        ([], 1000, 2500, 5000, 'Computer, general'),
    ],
    '5905': [  # Resistors
        ([], 0.05, 0.30, 1.0, 'Resistor'),
    ],
    '5910': [  # Capacitors
        (['tantalum', 'mil-prf-55365'], 1, 5, 15, 'Tantalum capacitor'),
        (['ceramic'], 0.10, 0.50, 2.0, 'Ceramic capacitor'),
        (['electrolytic', 'aluminum'], 0.50, 3, 10, 'Electrolytic capacitor'),
        ([], 0.20, 2, 8, 'Capacitor, general'),
    ],
    '5920': [  # Fuses
        ([], 1, 4, 10, 'Fuse'),
    ],
    '6210': [  # Indoor Lighting
        (['led', 'fixture'], 20, 80, 200, 'LED fixture'),
        (['bulb', 'lamp'], 2, 10, 30, 'Light bulb/lamp'),
        ([], 10, 40, 100, 'Lighting, general'),
    ],
    '6240': [  # Lamps
        ([], 2, 10, 30, 'Lamp/bulb'),
    ],
}


def _extract_part_numbers(description: str) -> list[str]:
    """Extract military and commercial part numbers from a description."""
    patterns = [
        r'MS\d{4,6}[A-Z]?\d*[-/]?\d*[A-Z]*',      # MS3106, MS27467-20-39P
        r'D38999/\d+[A-Z]+\d+[A-Z]*',                # D38999/26WJ61SN
        r'M39016/\d+[-]?\d*[A-Z]*',                   # M39016/6-137L
        r'M39019/\d+[-]?\d*[A-Z]*',                   # M39019 relays
        r'JANTXV?\d?[A-Z]?\d{4}[A-Z]*',              # JANTXV2N2222
        r'BA-\d{4}[A-Z]?/?[A-Z]*',                    # BA-5590/U
        r'BB-\d{4}[A-Z]?/?[A-Z]*',                    # BB-2590/U
        r'MIL-DTL-\d{4,6}[A-Z]?',                     # MIL-DTL-38999
        r'MIL-[A-Z]-\d{4,6}',                         # MIL-C-5015
        r'MIL-PRF-\d{4,6}',                            # MIL-PRF-55365
        r'\d{4}-\d{2}-\d{3}-\d{4}',                   # NSN format
    ]
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        found.extend(matches)
    return found


def _layer1_part_lookup(description: str) -> Optional[tuple]:
    """Layer 1: Match known part number patterns to price ranges."""
    desc_upper = description.upper()
    parts = _extract_part_numbers(description)

    # Check part numbers against known prices
    for part in parts:
        for pattern, (pmin, pavg, pmax, cat) in PART_NUMBER_PRICES.items():
            if re.search(pattern, part, re.IGNORECASE):
                return pmin, pavg, pmax, cat, 0.9, 'part_number'

    # Also check description directly against patterns
    for pattern, (pmin, pavg, pmax, cat) in PART_NUMBER_PRICES.items():
        if re.search(pattern, desc_upper):
            return pmin, pavg, pmax, cat, 0.85, 'part_number'

    return None


def _layer2_category_keyword(description: str, psc_code: str) -> Optional[tuple]:
    """Layer 2: Match by PSC category + keywords in description."""
    desc_lower = description.lower()

    # Try exact PSC match first
    if psc_code in CATEGORY_PRICES:
        subcategories = CATEGORY_PRICES[psc_code]
        for keywords, pmin, pavg, pmax, cat in subcategories:
            if keywords:  # Has specific keywords to match
                if any(kw in desc_lower for kw in keywords):
                    return pmin, pavg, pmax, cat, 0.7, 'category_keyword'
        # Fall through to category default (last entry, empty keywords)
        for keywords, pmin, pavg, pmax, cat in subcategories:
            if not keywords:
                return pmin, pavg, pmax, cat, 0.5, 'category_only'

    # Try matching by keywords across ALL categories
    for psc, subcategories in CATEGORY_PRICES.items():
        for keywords, pmin, pavg, pmax, cat in subcategories:
            if keywords and any(kw in desc_lower for kw in keywords):
                return pmin, pavg, pmax, cat, 0.6, 'category_keyword'

    return None


def _layer3_quantity_inference(
    total_obligation: float,
    unit_price_avg: float,
) -> int:
    """Layer 3: Estimate quantity from total obligation and unit price."""
    if unit_price_avg <= 0:
        return 1
    estimated_qty = max(1, round(total_obligation / unit_price_avg))
    # Sanity check — cap at reasonable quantities
    if estimated_qty > 100000:
        estimated_qty = max(1, round(total_obligation / (unit_price_avg * 5)))
    return estimated_qty


def estimate_price(
    description: str,
    psc_code: str,
    total_obligation: float,
) -> CommercialPrice:
    """Estimate commercial price for a government contract item.

    Uses a three-layer approach:
    1. Part number extraction and known price lookup
    2. Category + keyword classification with price ranges
    3. Quantity inference from total obligation

    Returns:
        CommercialPrice with estimated price, confidence, and metadata.
    """
    # Layer 1: Part number lookup
    result = _layer1_part_lookup(description)

    # Layer 2: Category + keyword fallback
    if result is None:
        result = _layer2_category_keyword(description, psc_code)

    # No match
    if result is None:
        return CommercialPrice(
            estimated_price=0,
            price_min=0,
            price_max=0,
            confidence=0,
            source='no_match',
            category_matched='Unknown',
            estimated_quantity=1,
            unit_price_estimate=0,
        )

    pmin, pavg, pmax, category, confidence, source = result

    # Layer 3: Quantity inference
    estimated_qty = _layer3_quantity_inference(total_obligation, pavg)

    return CommercialPrice(
        estimated_price=pavg * estimated_qty,
        price_min=pmin * estimated_qty,
        price_max=pmax * estimated_qty,
        confidence=confidence,
        source=source,
        category_matched=category,
        estimated_quantity=estimated_qty,
        unit_price_estimate=pavg,
    )
