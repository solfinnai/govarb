#!/usr/bin/env python3
"""GovArb Scanner — Government procurement arbitrage opportunity finder.

Scans USAspending.gov for COTS contracts and identifies pricing inefficiencies
by comparing government award amounts against estimated commercial prices.
"""

import argparse
import sys

from rich.console import Console

from analyzer import analyze_contracts
from config import DEFAULT_MIN_MARKUP, DEFAULT_SCAN_LIMIT, PSC_CATEGORIES
from pricing import estimate_price, CommercialPrice
from report import generate_markdown_report, print_report
from usaspending import Contract, USAspendingClient, get_sample_contracts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="govarb",
        description="Scan government contracts for COTS pricing arbitrage opportunities.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python scanner.py --dry-run                  Run with sample data\n"
            "  python scanner.py --categories 5935 6135      Scan connectors and batteries\n"
            "  python scanner.py --min-markup 10 --limit 50  High-markup scan\n"
            "  python scanner.py --output report.md          Save markdown report"
        ),
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        metavar="PSC",
        help=f"PSC codes to scan. Available: {', '.join(PSC_CATEGORIES.keys())}",
    )
    parser.add_argument(
        "--min-markup",
        type=float,
        default=DEFAULT_MIN_MARKUP,
        help=f"Minimum markup ratio to include (default: {DEFAULT_MIN_MARKUP})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SCAN_LIMIT,
        help=f"Max contracts to fetch from API (default: {DEFAULT_SCAN_LIMIT})",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write a markdown report to FILE",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use realistic sample data instead of hitting the API",
    )
    return parser.parse_args(argv)


def run_live(args: argparse.Namespace, console: Console) -> list:
    """Fetch live data from USAspending and analyze."""
    def progress(msg: str) -> None:
        console.print(f"[dim]{msg}[/dim]")

    # Validate PSC codes
    if args.categories:
        invalid = [c for c in args.categories if c not in PSC_CATEGORIES]
        if invalid:
            console.print(f"[red]Unknown PSC codes: {', '.join(invalid)}[/red]")
            console.print(f"[dim]Available: {', '.join(PSC_CATEGORIES.keys())}[/dim]")
            sys.exit(1)

    # Fetch contracts
    client = USAspendingClient(progress_callback=progress)
    contracts = client.search_contracts(
        psc_codes=args.categories,
        limit=args.limit,
    )

    if not contracts:
        console.print("[yellow]No contracts found.[/yellow]")
        return []

    # Price lookup
    progress("Looking up commercial prices...")
    prices: dict[str, CommercialPrice] = {}
    for contract in contracts:
        price = estimate_price(contract.description, contract.psc_code, contract.total_obligation)
        if price.confidence > 0:
            prices[contract.award_id] = price

    progress(f"Matched commercial prices for {len(prices)}/{len(contracts)} contracts")

    # Analyze
    return analyze_contracts(contracts, prices, min_markup=args.min_markup)


def run_dry(console: Console) -> list:
    """Run with sample data."""
    console.print("[dim]Using sample data (--dry-run mode)[/dim]")
    contracts = get_sample_contracts()
    prices: dict[str, CommercialPrice] = {}
    for contract in contracts:
        price = estimate_price(contract.description, contract.psc_code, contract.total_obligation)
        if price.confidence > 0:
            prices[contract.award_id] = price
    return analyze_contracts(contracts, prices, min_markup=1.0, min_score=0)


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = parse_args(argv)
    console = Console()

    console.print("[bold blue]GovArb Scanner[/bold blue] v1.0")
    console.print()

    # Fetch + analyze
    if args.dry_run:
        opportunities = run_dry(console)
    else:
        opportunities = run_live(args, console)

    # Report
    print_report(opportunities, console=console, dry_run=args.dry_run)

    if args.output:
        path = generate_markdown_report(
            opportunities, args.output, dry_run=args.dry_run,
        )
        console.print(f"[green]Report saved to {path}[/green]")


if __name__ == "__main__":
    main()
