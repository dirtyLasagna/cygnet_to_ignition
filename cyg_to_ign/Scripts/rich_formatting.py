from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()

def chunk_list(lst, n_cols):
    # Splits lst into n_cols columns as evently as possible
    avg = len(lst) // n_cols
    remainder = len(lst) % n_cols
    chunks = []
    start = 0
    for i in range(n_cols):
        end = start + avg + (1 if i < remainder else 0)
        chunks.append(lst[start:end])
        start = end
    
    # Pad columns to equal length
    max_len = max(len(chunk) for chunk in chunks)
    for chunk in chunks:
        while len(chunk) < max_len:
            chunk.append("")
    return chunks

def display_list_as_columns(title, items, n_cols=3):
    table = Table(title=f"{title} ({len(items)})", show_lines=True)
    for i in range(n_cols):
        table.add_column(f"Col {i+1}", style="bold")
    columns = chunk_list(items, n_cols)
    for row in zip(*columns):
        table.add_row(*row)
    return table

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

def display_pnt_summary(summary):

    # calculate n_cols
    n_cols = min(5, max(1, len(summary['Full Rows']) // 10))

    # Main Panel
    console.print(Panel("[bold cyan]PNT File Analysis Summary[/bold cyan]", border_style="blue", title_align="left"))

    # General Info Panel
    general_info = (
        f"[bold]Total Rows: [/bold] {summary['Total Rows']}\n"
        f"[bold]Unique UDC Count:[/bold] {summary['Unique UDC Count']}\n"
        f"[bold]Unique Desc Count:[/bold] {summary['Unique Desc Count']}\n"
        f"[bold]Number of Fully Populated Columns:[/bold] {len(summary['Full Rows'])}\n"
        f"[bold]Columns with Missing Values:[/bold] {len(summary['Missing Values'])} / 235\n"
        f"[bold]Number of Fully Empty Columns:[/bold] {len(summary['Empty Categories'])}\n"
        f"[bold]Number of Unaccounted Column Headers:[/bold] {len(summary['Unaccounted Columns'])}\n"
        f"[bold]Unaccounted Column Headers List:[/bold] {summary['Unaccounted Columns']}"

    )
    console.print(Panel.fit(general_info, title="General Info", border_style="blue"))

    # Full Rows Panel
    #full_rows_text = "\n".join(summary['Full Rows']) if summary['Full Rows'] else "None"
    #console.print(Panel(full_rows_text, title="Fully Populated Columns", border_style="green"))
    full_table = display_list_as_columns("Fully Populated Columns", summary['Full Rows'], n_cols)
    console.print(full_table)

    # Empty Categories Panel
    #empty_text = "\n".join(summary['Empty Categories']) if summary['Empty Categories'] else "None"
    #console.print(Panel(empty_text, title="Empty Categories", border_style="red"))
    empty_table = display_list_as_columns("Empty Categories", summary['Empty Categories'], n_cols)
    console.print(empty_table)

    # Missing Values Table
    table = Table(show_lines=True)
    table.add_column("Column", style="bold yellow")
    table.add_column("Missing Count", justify="center")
    table.add_column("Percent", justify="center")
    for col, vals in summary['Missing Values'].items():
        table.add_row(col, str(vals['count']), vals['percent'])
    console.print(Panel.fit(table, title="Columns with Missing Values", border_style="magenta"))

    return

def display_fac_summary(summary):

    # Main Panel
    console.print( Panel( 
        "[bold cyan]FAC File Analysis Summary[/bold cyan]", border_style="blue", title_align="left"
    ))

    
    total_count_column = summary['Column Summary']['Total Columns']
    fullyPopulatedPercentage = round(float(summary['Column Summary']['Fully Populated']) / float(total_count_column) * 100, 2) 
    fullyEmptyPercentage = round(float(summary['Column Summary']['Fully Empty']) / float(total_count_column) * 100, 2)
    partiallyFilledPercentage = round(float(summary['Column Summary']['Partially Filled']) / float(total_count_column) * 100, 2)

    # General Info & Column Summary horizontally
    general_info = (
        f"[bold]Total Rows:[/bold] {summary['Total Rows']}\n"
        f"[bold]Total Columns:[/bold] {total_count_column}\n"
    )
    
    col_summary = (
        f"[bold]Fully Populated:[/bold] \t {summary['Column Summary']['Fully Populated']} / {total_count_column} - {fullyPopulatedPercentage} %\n"
        f"[bold]Fully Empty:[/bold] \t\t {summary['Column Summary']['Fully Empty']} / {total_count_column} - {fullyEmptyPercentage} %\n"
        f"[bold]Partially Filled:[/bold] \t {summary['Column Summary']['Partially Filled']} / {total_count_column} - {partiallyFilledPercentage} %\n"
    )
    
    console.print(Columns([
        Panel(general_info, title="General Info", border_style="blue"),
        Panel(col_summary, title="Column Summary", border_style="cyan", width=50)
    ]))

    # Key Column Statistics Table
    key_table = Table(show_lines=True)
    key_table.add_column("Column", style="bold green")
    key_table.add_column("Unique Values", justify="center")
    key_table.add_column("Non-Empty", justify="center")
    key_table.add_column("Filled %", justify="center")
    
    for col, stats in summary['Key Column Statistics'].items():
        key_table.add_row(
            col,
            str(stats['Unique Values']),
            stats['Non-Empty'],
            stats['Filled Percent']
        )
    
    console.print(Panel(key_table, title="Key Columns Analysis", border_style="green"))

    # Full Columns (100% populated)
    if summary['Full Columns']:
        n_cols = min(5, max(1, len(summary['Full Columns']) // 10))
        full_table = display_list_as_columns("Fully Populated Columns", summary['Full Columns'], n_cols)
        #console.print(full_table)
    else:
        console.print(Panel("[yellow]No fully populated columns found[/yellow]", title="Fully Populated Columns", border_style="green"))

    # Empty Columns
    if summary['Empty Columns']:
        empty_list = summary['Empty Columns']
        empty_text = "\n".join(empty_list) if empty_list else "None"
        #console.print(Panel(empty_text, title="100% Empty Columns", border_style="purple"))

    # Partially Empty Columns
    if summary['Missing Values']:
        mixed_list = summary['Missing Values']
        mixed_text = "\n".join(mixed_list) if mixed_list else "None"
        #console.print(Panel(mixed_text, title="Partially Empty Columns", border_style="magenta"))

    # Missing Values Table (only columns with missing data)
    if summary['Missing Values']:
        missing_table = Table(show_lines=True)
        missing_table.add_column("Column", style="bold yellow")
        missing_table.add_column("Missing Count", justify="center")
        missing_table.add_column("Percent Missing", justify="center")
        
        for col, vals in summary['Missing Values'].items():
            missing_table.add_row(col, str(vals['count']), vals['percent'])
        
        console.print(Panel(missing_table, title="Columns with Missing Values", border_style="magenta"))
    else:
        console.print(Panel("[green]No missing values found - all columns fully populated![/green]", title="Missing Values", border_style="green"))

    return 