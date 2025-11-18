from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()

def display_trs_summary(summary):
    # PANEL LAYOUT: 
    # --------------------------------
    #   Main Panel
        # Sections as Tables:
            # General Info
            # Column Stats
                # Non-Empty Counts
                # Percentage Counts
                # Unique Header Counts
            # Empty Columns
            # Missing Values
            # Focus Table (~UDCAll)
    # --------------------------------

    # Main Panel
    console.print(Panel("[bold cyan]TRS File Analysis Summary[/bold cyan]", border_style="blue", title_align="left"))

    # Combine General and Empty info horizontally
    console.print(Columns([
    Panel(
        f"[bold]Total Rows:[/bold] {summary['Total Rows']}\n"
        f"[bold]Headers:[/bold] {', '.join(summary['Headers'])}",
        title="General Info",
        border_style="blue"
    ),
    Panel("\n".join(summary['Empty Columns']), title="Empty Columns", border_style="red")
], equal=True))


    # Column Stats - Non-Empty Counts Table
    table1 = Table(show_lines=True)
    table1.add_column("Column", style="bold magenta")
    table1.add_column("Non-Empty", justify="center")
    table1.add_column("Percent", justify="center")
    for col in summary['Headers']:
        table1.add_row(col, summary['Non Empty Counts Per Column'][col], summary['Percentage Count'][col])

    # Column Stats - Unique Header Counts
    table2 = Table(show_lines=True)
    table2.add_column("Column", style="bold green")
    table2.add_column("Distinct Count", justify="center")
    for col, count in summary['Unique Header Count'].items():
        table2.add_row(col, str(count))

    # Missing Value Tables
    table3 = Table(show_lines=True)
    table3.add_column("Column", style="bold yellow")
    table3.add_column("Fraction", justify="center")
    table3.add_column("Percent", justify="center")
    for col, vals in summary['Missing Values'].items():
        table3.add_row(col, vals['Fraction'], vals['Percent'])

    # Combines tables horizonatally 
    console.print(Columns([
        Panel(table1, title="Non-Empty & Percentages", border_style="cyan"),
        Panel(table2, title="Unique Header Counts", border_style="green"),
        Panel(table3, title="Missing Values", border_style="yellow")
    ], equal=True))

    # Focus Table Panel
    focus = summary['Focus TABLE (~UDCALL)']
    focus_text = (
        f"[bold]Row Count:[/bold] {focus['Row Count']}\n"
        f"[bold]Percent of Total:[/bold] {focus['Percent of Total']}%\n"
        f"[bold]Distinct ENTRY:[/bold] {focus['Distinct ENTRY']}\n"
        f"[bold]Distinct DESC:[/bold] {focus['Distinct DESC']}"
    )
    console.print(Panel.fit(focus_text, title="Focus TABLE (~UDCALL)", border_style="green"))
    return