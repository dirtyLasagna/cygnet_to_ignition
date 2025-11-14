from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.rule import Rule

from cyg_to_ign.Scripts.parse_trs import run

console = Console()

# ---------------------------
# Command: parse-trs
# ---------------------------
def parse_trs(input_file: str, output_file: str):
    """
    Parse TRS data from Cygnet and convert to Ignition format.
    """
    console.print(Panel(f"[bold green]Parsing TRS[/bold green]\nInput: {input_file}\nOutput: {output_file}"))
    
    # TODO: Add your conversion logic here
    # Example placeholder:
    console.print("[yellow]Processing TRS tags...[/yellow]")
    
    # Simulate summary table
    table = Table(title="TRS Conversion Summary")
    table.add_column("Tag", style="cyan")
    table.add_column("Status", style="green")
    table.add_row("TRS_TAG_001", "Success")
    table.add_row("TRS_TAG_002", "Failed")
    console.print(table)

    console.print("[bold blue]TRS parsing complete![/bold blue]")

# ---------------------------
# Command: parse-pnt
# ---------------------------
def parse_pnt(input_file: str, output_file: str):
    """
    Parse PNT data from Cygnet and convert to Ignition format.
    """
    console.print(Panel(f"[bold green]Parsing PNT[/bold green]\nInput: {input_file}\nOutput: {output_file}"))
    
    # TODO: Add your conversion logic here
    console.print("[yellow]Processing PNT points...[/yellow]")
    console.print("[bold blue]PNT parsing complete![/bold blue]")

# ---------------------------
# Command: parse-fac
# ---------------------------
def parse_fac(input_file: str, output_file: str):
    """
    Parse FAC data from Cygnet and convert to Ignition format.
    """
    console.print(Panel(f"[bold green]Parsing FAC[/bold green]\nInput: {input_file}\nOutput: {output_file}"))
    
    # TODO: Add your conversion logic here
    console.print("[yellow]Processing FAC facilities...[/yellow]")
    console.print("[bold blue]FAC parsing complete![/bold blue]")

# ---------------------------
# Endless Loop:
# ---------------------------
def main():
    while True:
        try:
            user_input = Prompt.ask("[bold blue]>>>[/bold blue]").strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]Input cancelled (Ctrl+C). Type 'exit' or 'q' to quit.[/yellow]")
            continue

        if user_input.lower() in {"q", "exit", "quit"}:
            console.print("[bold red]Exiting CLI...[/bold red]")
            break
        
        elif user_input == "help":
            console.print("\n[bold cyan]Available commands:[/bold cyan]\n")
            console.print(
                "[yellow]test[/yellow]\t\t– always testing"
            )
            console.print(
                "[yellow]parse-trs[/yellow]\t– Work in progress command"
            )
            console.print(
                "[yellow]help[/yellow]\t\t– Show this help message"
            )
            console.print(
                "[yellow]q, exit, quit[/yellow]\t– Quit the CLI\n"
            )
            continue

        if user_input.lower() == "test":
            console.print("yo you are testing dude! keep it up man.")
            continue
        
        # add in your other user_input commands
        # =============================================================
        if user_input.lower() == "parse-trs":
            console.print("Within the 'cygnet_input' folder ...")
            csv_name = Prompt.ask("Type the filename of the cygnet trs CSV file").strip()
            
            continue
        
        else:
            console.print(f"[red]Unknown command: [/red] {user_input!r}\n")

    console.print(Rule(style="dim"))
    console.print(
        Panel.fit("[bold green]take care\n          o7 [/bold green]")
    )

# ---------------------------
# Entry Point
# ---------------------------
if __name__ == "__main__":
    main()