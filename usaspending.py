"""USAspending.gov API client for fetching government contract data."""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import requests

from config import (
    AWARD_DETAIL_ENDPOINT,
    AWARD_TYPE_CODES,
    PSC_CATEGORIES,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SEARCH_ENDPOINT,
)


@dataclass
class Contract:
    """Represents a government contract award."""

    award_id: str
    piid: str  # Procurement Instrument Identifier
    description: str
    total_obligation: float
    recipient_name: str
    awarding_agency: str
    psc_code: str
    psc_description: str
    naics_code: str
    naics_description: str
    number_of_offers: Optional[int]
    extent_competed: str
    commercial_item_description: str
    set_aside_type: str
    award_date: str
    is_single_bidder: bool
    is_commercial: bool

    @property
    def is_recent(self) -> bool:
        """Check if contract was awarded within the last 12 months."""
        try:
            award_dt = datetime.strptime(self.award_date, "%Y-%m-%d")
            return award_dt > datetime.now() - timedelta(days=365)
        except (ValueError, TypeError):
            return False


class USAspendingClient:
    """Client for the USAspending.gov API."""

    def __init__(self, progress_callback: Optional[callable] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "GovProcurementScanner/1.0",
        })
        self._last_request_time = 0.0
        self._progress = progress_callback or (lambda msg: None)

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _post(self, url: str, payload: dict) -> dict:
        """Make a rate-limited POST request."""
        self._rate_limit()
        resp = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()

    def _get(self, url: str) -> dict:
        """Make a rate-limited GET request."""
        self._rate_limit()
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()

    def search_contracts(
        self,
        psc_codes: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[Contract]:
        """Search for COTS contracts by PSC codes.

        Args:
            psc_codes: Product Service Codes to search. Defaults to all configured categories.
            limit: Maximum number of contracts to return.

        Returns:
            List of Contract objects matching the search criteria.
        """
        codes = psc_codes or list(PSC_CATEGORIES.keys())
        self._progress(f"Searching USAspending for PSC codes: {', '.join(codes)}")

        # Build the search payload
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "filters": {
                "award_type_codes": AWARD_TYPE_CODES,
                "time_period": [{"start_date": one_year_ago, "end_date": today}],
                "psc_codes": codes,
            },
            "fields": [
                "Award ID",
                "Description",
                "Award Amount",
                "Recipient Name",
                "Awarding Agency",
                "Product or Service Code",
                "NAICS Code",
                "Start Date",
            ],
            "page": 1,
            "limit": limit,
            "sort": "Award Amount",
            "order": "desc",
            "subawards": False,
        }

        try:
            data = self._post(SEARCH_ENDPOINT, payload)
        except requests.RequestException as e:
            self._progress(f"Error searching contracts: {e}")
            return []

        results = data.get("results", [])
        self._progress(f"Found {len(results)} awards, fetching details...")

        contracts = []
        for i, result in enumerate(results):
            award_id = result.get("internal_id") or result.get("generated_internal_id", "")
            if not award_id:
                continue

            self._progress(f"  Fetching detail {i + 1}/{len(results)}: {result.get('Award ID', 'N/A')}")
            contract = self._fetch_award_detail(award_id, result)
            if contract:
                contracts.append(contract)

        self._progress(f"Retrieved {len(contracts)} contract details")
        return contracts

    def _fetch_award_detail(self, award_id: str, summary: dict) -> Optional[Contract]:
        """Fetch detailed information for a specific award.

        Args:
            award_id: The generated unique award ID.
            summary: Summary data from the search results.

        Returns:
            A Contract object, or None if the detail fetch fails.
        """
        try:
            detail = self._get(f"{AWARD_DETAIL_ENDPOINT}/{award_id}/")
        except requests.RequestException as e:
            self._progress(f"    Warning: Could not fetch detail for {award_id}: {e}")
            return None

        latest_txn = detail.get("latest_transaction_contract_data", {}) or {}
        psc = detail.get("psc_hierarchy", {}) or {}
        naics = detail.get("naics_hierarchy", {}) or {}
        recipient = detail.get("recipient_hash", "")

        number_of_offers_raw = latest_txn.get("number_of_offers_received")
        try:
            number_of_offers = int(number_of_offers_raw) if number_of_offers_raw else None
        except (ValueError, TypeError):
            number_of_offers = None

        extent_competed = latest_txn.get("extent_competed_description", "") or ""
        commercial_desc = latest_txn.get("commercial_item_acquisition_description", "") or ""
        set_aside = latest_txn.get("type_of_set_aside_description", "") or ""

        psc_code_raw = psc.get("base_code", summary.get("Product or Service Code", ""))
        psc_code = str(psc_code_raw) if not isinstance(psc_code_raw, dict) else psc_code_raw.get("code", "")
        total_obligation = detail.get("total_obligation", 0) or summary.get("Award Amount", 0) or 0

        return Contract(
            award_id=str(award_id),
            piid=detail.get("piid", summary.get("Award ID", "")),
            description=detail.get("description", summary.get("Description", "")),
            total_obligation=float(total_obligation),
            recipient_name=detail.get("recipient_name", summary.get("Recipient Name", "Unknown")),
            awarding_agency=detail.get("awarding_agency_name", summary.get("Awarding Agency", "")),
            psc_code=psc_code,
            psc_description=PSC_CATEGORIES.get(psc_code, psc.get("base_code_description", "")),
            naics_code=naics.get("code", summary.get("NAICS Code", "")),
            naics_description=naics.get("description", ""),
            number_of_offers=number_of_offers,
            extent_competed=extent_competed,
            commercial_item_description=commercial_desc,
            set_aside_type=set_aside,
            award_date=detail.get("date_signed", summary.get("Start Date", "")),
            is_single_bidder=number_of_offers == 1,
            is_commercial="COMMERCIAL" in commercial_desc.upper() if commercial_desc else False,
        )


def get_sample_contracts() -> list[Contract]:
    """Return realistic sample contracts for dry-run mode."""
    return [
        Contract(
            award_id="SAMPLE-001",
            piid="W56HZV-25-C-0847",
            description="CONNECTOR,PLUG,ELECTRICAL - MS3126F20-39P, MIL-DTL-26482",
            total_obligation=47_250.00,
            recipient_name="AMPHENOL AEROSPACE OPERATIONS",
            awarding_agency="DEPT OF THE ARMY",
            psc_code="5935",
            psc_description="Connectors, Electrical",
            naics_code="334417",
            naics_description="Electronic Connector Manufacturing",
            number_of_offers=1,
            extent_competed="NOT COMPETED UNDER SAP",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2025-11-14",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-002",
            piid="SPE7LX-25-D-0293",
            description="BATTERY,NONRECHARGEABLE - BA-5590/U LITHIUM SULFUR DIOXIDE",
            total_obligation=892_400.00,
            recipient_name="SAFT AMERICA INC",
            awarding_agency="DEFENSE LOGISTICS AGENCY",
            psc_code="6135",
            psc_description="Batteries, Primary",
            naics_code="335912",
            naics_description="Primary Battery Manufacturing",
            number_of_offers=1,
            extent_competed="NOT AVAILABLE FOR COMPETITION",
            commercial_item_description="COMMERCIAL ITEM USING FAR 12",
            set_aside_type="",
            award_date="2026-01-08",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-003",
            piid="N00383-25-C-1472",
            description="RELAY,ELECTROMAGNETIC - M39016/6-137L, DPDT 28VDC 10A",
            total_obligation=168_750.00,
            recipient_name="TE CONNECTIVITY CORPORATION",
            awarding_agency="DEPT OF THE NAVY",
            psc_code="5945",
            psc_description="Relays and Solenoids",
            naics_code="335314",
            naics_description="Relay and Industrial Control Manufacturing",
            number_of_offers=1,
            extent_competed="FOLLOW ON TO COMPETED ACTION",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2025-08-22",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-004",
            piid="FA8532-25-F-0064",
            description="MICROCIRCUIT,DIGITAL - 5962-01-519-1742, FPGA XILINX VIRTEX XQRV600",
            total_obligation=2_340_000.00,
            recipient_name="MICROCHIP TECHNOLOGY INC",
            awarding_agency="DEPT OF THE AIR FORCE",
            psc_code="5962",
            psc_description="Microcircuits, Electronic",
            naics_code="334413",
            naics_description="Semiconductor and Related Device Manufacturing",
            number_of_offers=1,
            extent_competed="NOT COMPETED UNDER SAP",
            commercial_item_description="COMMERCIAL ITEM USING FAR 12",
            set_aside_type="",
            award_date="2025-12-03",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-005",
            piid="W911QY-26-P-0188",
            description="COMPUTER,TABLET - RUGGED MIL-STD-810H, PANASONIC TOUGHBOOK FZ-G2",
            total_obligation=1_875_000.00,
            recipient_name="PANASONIC CONNECT NORTH AMERICA",
            awarding_agency="DEPT OF THE ARMY",
            psc_code="7025",
            psc_description="ADP Input/Output and Storage Devices",
            naics_code="334111",
            naics_description="Electronic Computer Manufacturing",
            number_of_offers=2,
            extent_competed="FULL AND OPEN COMPETITION",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2026-02-17",
            is_single_bidder=False,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-006",
            piid="SPE7M1-25-D-0415",
            description="CABLE ASSEMBLY,SPECIAL - W81A/U, MIL-DTL-17, 50 OHM RF COAXIAL 6FT",
            total_obligation=324_600.00,
            recipient_name="TIMES MICROWAVE SYSTEMS INC",
            awarding_agency="DEFENSE LOGISTICS AGENCY",
            psc_code="6145",
            psc_description="Wire and Cable, Electrical",
            naics_code="335929",
            naics_description="Other Communication Wire Manufacturing",
            number_of_offers=1,
            extent_competed="NOT COMPETED UNDER SAP",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2025-09-30",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-007",
            piid="N68335-26-C-0039",
            description="SEMICONDUCTOR DEVICE,TRANSISTOR - JANTXV2N2222A, NPN SWITCHING",
            total_obligation=89_100.00,
            recipient_name="VISHAY INTERTECHNOLOGY INC",
            awarding_agency="DEPT OF THE NAVY",
            psc_code="5961",
            psc_description="Semiconductor Devices and Associated Hardware",
            naics_code="334413",
            naics_description="Semiconductor and Related Device Manufacturing",
            number_of_offers=1,
            extent_competed="NOT AVAILABLE FOR COMPETITION",
            commercial_item_description="COMMERCIAL ITEM USING FAR 12",
            set_aside_type="",
            award_date="2026-01-22",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-008",
            piid="W56HZV-25-P-3241",
            description="LUG,TERMINAL - MS25036-153, RING TONGUE CRIMP 8AWG #10 STUD",
            total_obligation=12_480.00,
            recipient_name="THOMAS & BETTS CORPORATION",
            awarding_agency="DEPT OF THE ARMY",
            psc_code="5940",
            psc_description="Lugs, Terminals, and Terminal Strips",
            naics_code="335931",
            naics_description="Current-Carrying Wiring Device Manufacturing",
            number_of_offers=1,
            extent_competed="NOT COMPETED UNDER SAP",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2025-10-05",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-009",
            piid="FA8501-26-F-0112",
            description="COMPUTER,SERVER - DELL POWEREDGE R760, XEON 8470 52-CORE, 512GB DDR5",
            total_obligation=4_128_000.00,
            recipient_name="DELL FEDERAL SYSTEMS LP",
            awarding_agency="DEPT OF THE AIR FORCE",
            psc_code="7025",
            psc_description="ADP Input/Output and Storage Devices",
            naics_code="334111",
            naics_description="Electronic Computer Manufacturing",
            number_of_offers=1,
            extent_competed="COMPETED UNDER SAP",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="SMALL BUSINESS SET-ASIDE",
            award_date="2026-03-01",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-010",
            piid="SPE4A7-25-D-0877",
            description="ELECTRICAL COMPONENT,MISC - CIRCUIT BREAKER THERMAL 15A 250VAC MIL-PRF-39019",
            total_obligation=156_200.00,
            recipient_name="SENSATA TECHNOLOGIES INC",
            awarding_agency="DEFENSE LOGISTICS AGENCY",
            psc_code="5999",
            psc_description="Electrical and Electronic Components, Misc",
            naics_code="335313",
            naics_description="Switchgear and Switchboard Apparatus Manufacturing",
            number_of_offers=1,
            extent_competed="NOT COMPETED UNDER SAP",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2025-07-18",
            is_single_bidder=True,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-011",
            piid="DAAB07-26-C-0051",
            description="IT EQUIPMENT - CISCO CATALYST 9300-48P SWITCH, POE+ 48-PORT MANAGED",
            total_obligation=738_500.00,
            recipient_name="WORLD WIDE TECHNOLOGY INC",
            awarding_agency="DEPT OF THE ARMY",
            psc_code="7035",
            psc_description="ADP Support Equipment",
            naics_code="334210",
            naics_description="Telephone Apparatus Manufacturing",
            number_of_offers=3,
            extent_competed="FULL AND OPEN COMPETITION",
            commercial_item_description="COMMERCIAL ITEM",
            set_aside_type="",
            award_date="2026-02-04",
            is_single_bidder=False,
            is_commercial=True,
        ),
        Contract(
            award_id="SAMPLE-012",
            piid="N00024-25-C-6218",
            description="CONNECTOR,RECEPTACLE - D38999/26WJ61SN, FILTERED EMI/RFI MIL-DTL-38999 SERIES III",
            total_obligation=534_000.00,
            recipient_name="GLENAIR INC",
            awarding_agency="DEPT OF THE NAVY",
            psc_code="5935",
            psc_description="Connectors, Electrical",
            naics_code="334417",
            naics_description="Electronic Connector Manufacturing",
            number_of_offers=1,
            extent_competed="ONLY ONE SOURCE",
            commercial_item_description="COMMERCIAL ITEM USING FAR 12",
            set_aside_type="",
            award_date="2025-06-11",
            is_single_bidder=True,
            is_commercial=True,
        ),
    ]
