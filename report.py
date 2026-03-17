"""Report generation for arbitrage opportunities."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from tabulate import tabulate

from analyzer import Opportunity


def _truncate(text: str, length: int = 50) -> str:
    """Truncate text with ellipsis."""
    return text[:length - 1] + "…" if len(text) > length else text


def _format_currency(amount: float) -> str:
    """Format a number as USD currency."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:,.0f}"


def _format_markup(ratio: float) -> str:
    """Format markup ratio."""
    return f"{ratio:.1f}x"


def _score_color(score: int) -> str:
    """Return a rich color name based on score."""
    if score >= 90:
        return "bold red"
    if score >= 75:
        return "bold yellow"
    if score >= 60:
        return "yellow"
    return "green"


def print_report(
    opportunities: list[Opportunity],
    console: Optional[Console] = None,
    dry_run: bool = False,
) -> None:
    """Print a rich-formatted report to the terminal.

    Args:
        opportunities: Scored opportunities sorted by rank.
        console: Rich Console instance. Creates one if not provided.
        dry_run: Whether this is a dry-run (shown in header).
    """
    console = console or Console()

    if not opportunities:
        console.print("[yellow]No opportunities found matching criteria.[/yellow]")
        return

    # Header
    mode = " [DRY RUN]" if dry_run else ""
    total_value = sum(o.addressable_value for o in opportunities)
    console.print()
    console.print(Panel(
        f"[bold]GovArb Scanner Results{mode}[/bold]\n"
        f"Found [cyan]{len(opportunities)}[/cyan] opportunities | "
        f"Total addressable value: [green]{_format_currency(total_value)}[/green]",
        border_style="blue",
    ))

    # Build table
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Contract ID", width=22)
    table.add_column("Description", width=45)
    table.add_column("Award Amt", justify="right", width=10)
    table.add_column("Est Comm.", justify="right", width=10)
    table.add_column("Markup", justify="right", width=8)
    table.add_column("Bids", justify="center", width=5)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Recipient", width=25)

    for rank, opp in enumerate(opportunities, 1):
        c = opp.contract
        score_style = _score_color(opp.opportunity_score)
        bidders = str(c.number_of_offers) if c.number_of_offers is not None else "N/A"

        table.add_row(
            str(rank),
            c.piid,
            _truncate(c.description, 45),
            _format_currency(c.total_obligation),
            _format_currency(opp.commercial_price.estimated_price),
            _format_markup(opp.markup_ratio),
            bidders,
            f"[{score_style}]{opp.opportunity_score}[/{score_style}]",
            _truncate(c.recipient_name, 25),
        )

    console.print(table)
    console.print()


def generate_markdown_report(
    opportunities: list[Opportunity],
    output_path: str,
    dry_run: bool = False,
) -> str:
    """Generate a markdown report file.

    Args:
        opportunities: Scored opportunities sorted by rank.
        output_path: File path to write the markdown report.
        dry_run: Whether this is a dry-run.

    Returns:
        The output file path.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = " (DRY RUN)" if dry_run else ""
    total_value = sum(o.addressable_value for o in opportunities)

    lines = [
        f"# GovArb Scanner Report{mode}",
        f"",
        f"**Generated:** {now}  ",
        f"**Opportunities found:** {len(opportunities)}  ",
        f"**Total addressable value:** {_format_currency(total_value)}",
        f"",
        f"---",
        f"",
    ]

    if not opportunities:
        lines.append("_No opportunities found matching criteria._")
    else:
        # Summary table using tabulate
        headers = [
            "Rank", "Contract ID", "Description", "Award Amount",
            "Est Commercial", "Markup", "Bidders", "Score", "Recipient",
        ]
        rows = []
        for rank, opp in enumerate(opportunities, 1):
            c = opp.contract
            bidders = str(c.number_of_offers) if c.number_of_offers is not None else "N/A"
            rows.append([
                rank,
                c.piid,
                _truncate(c.description, 50),
                _format_currency(c.total_obligation),
                _format_currency(opp.commercial_price.estimated_price),
                _format_markup(opp.markup_ratio),
                bidders,
                opp.opportunity_score,
                _truncate(c.recipient_name, 30),
            ])

        lines.append("## Top Opportunities")
        lines.append("")
        lines.append(tabulate(rows, headers=headers, tablefmt="github"))
        lines.append("")

        # Detailed breakdown
        lines.append("---")
        lines.append("")
        lines.append("## Detailed Analysis")
        lines.append("")

        for rank, opp in enumerate(opportunities, 1):
            c = opp.contract
            cp = opp.commercial_price
            bidders = str(c.number_of_offers) if c.number_of_offers is not None else "N/A"

            lines.append(f"### #{rank}: {c.piid}")
            lines.append(f"")
            lines.append(f"- **Description:** {c.description}")
            lines.append(f"- **Award Amount:** {_format_currency(c.total_obligation)}")
            lines.append(f"- **Est. Commercial Price:** {_format_currency(cp.estimated_price)}")
            lines.append(f"- **Markup:** {_format_markup(opp.markup_ratio)}")
            lines.append(f"- **Addressable Value:** {_format_currency(opp.addressable_value)}")
            lines.append(f"- **Score:** {opp.opportunity_score}/100")
            lines.append(f"- **Bidders:** {bidders}")
            lines.append(f"- **Recipient:** {c.recipient_name}")
            lines.append(f"- **Agency:** {c.awarding_agency}")
            lines.append(f"- **Award Date:** {c.award_date}")
            lines.append(f"- **Category:** {cp.item_category}")
            lines.append(f"- **Price Source:** {cp.source}")
            lines.append(f"- **Notes:** {cp.notes}")
            lines.append(f"- **Score Breakdown:** {opp.score_breakdown}")
            lines.append(f"")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path
