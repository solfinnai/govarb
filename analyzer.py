"""Arbitrage opportunity scoring and analysis engine."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from config import MARKUP_SCORE_TIERS, SCORING_WEIGHTS
from pricing import CommercialPrice
from usaspending import Contract


@dataclass
class Opportunity:
    """A scored arbitrage opportunity."""

    contract: Contract
    commercial_price: CommercialPrice
    markup_ratio: float
    opportunity_score: int
    score_breakdown: dict[str, int]
    addressable_value: float  # contract_amount - commercial_price

    @property
    def rank_key(self) -> tuple[int, float]:
        """Sort key: score descending, then markup descending."""
        return (-self.opportunity_score, -self.markup_ratio)


def _score_markup(ratio: float) -> int:
    """Score based on markup ratio using configured tiers."""
    for threshold, score in MARKUP_SCORE_TIERS:
        if ratio >= threshold:
            return score
    return 0


def score_opportunity(
    contract: Contract,
    commercial_price: CommercialPrice,
) -> Opportunity:
    """Calculate the arbitrage opportunity score for a contract.

    Args:
        contract: The government contract.
        commercial_price: The estimated commercial equivalent price.

    Returns:
        A fully scored Opportunity object.
    """
    if commercial_price.estimated_price <= 0:
        markup = 0.0
    else:
        markup = contract.total_obligation / commercial_price.estimated_price

    breakdown: dict[str, int] = {}

    # Base score from markup ratio
    base = _score_markup(markup)
    breakdown["markup_base"] = base

    # Single bidder bonus
    single = SCORING_WEIGHTS["single_bidder_bonus"] if contract.is_single_bidder else 0
    breakdown["single_bidder"] = single

    # No set-aside bonus (unrestricted = less competition pressure)
    no_set_aside = SCORING_WEIGHTS["no_set_aside_bonus"] if not contract.set_aside_type else 0
    breakdown["no_set_aside"] = no_set_aside

    # COTS designation bonus
    cots = SCORING_WEIGHTS["cots_designation_bonus"] if contract.is_commercial else 0
    breakdown["cots_designation"] = cots

    # Recency bonus
    recent = SCORING_WEIGHTS["recent_contract_bonus"] if contract.is_recent else 0
    breakdown["recent_contract"] = recent

    total_score = min(100, base + single + no_set_aside + cots + recent)
    addressable = max(0, contract.total_obligation - commercial_price.estimated_price)

    return Opportunity(
        contract=contract,
        commercial_price=commercial_price,
        markup_ratio=markup,
        opportunity_score=total_score,
        score_breakdown=breakdown,
        addressable_value=addressable,
    )


def analyze_contracts(
    contracts: list[Contract],
    prices: dict[str, CommercialPrice],
    min_markup: float = 5.0,
    min_score: int = 50,
) -> list[Opportunity]:
    """Analyze a list of contracts against commercial prices and return scored opportunities.

    Args:
        contracts: List of government contracts.
        prices: Mapping of award_id → CommercialPrice.
        min_markup: Minimum markup ratio to include in results.
        min_score: Minimum opportunity score to include in results.

    Returns:
        List of Opportunity objects, sorted by score descending.
    """
    opportunities: list[Opportunity] = []

    for contract in contracts:
        price = prices.get(contract.award_id)
        if price is None:
            continue

        opp = score_opportunity(contract, price)

        if opp.markup_ratio >= min_markup and opp.opportunity_score >= min_score:
            opportunities.append(opp)

    opportunities.sort(key=lambda o: o.rank_key)
    return opportunities
