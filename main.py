# path
from pathlib import Path

# rich library
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.rule import Rule

# common
from cyg_to_ign.Scripts.common  import getRootFolder

# parse functions
from cyg_to_ign.Scripts.parse_trs import runParseTRS
from cyg_to_ign.Scripts.parse_pnt import runParsePNT

# rich formatting
from cyg_to_ign.Scripts.rich_formatting import display_trs_summary

console = Console()

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
            test = getRootFolder()
            console.print("test: ", test)
            continue
        
        # =============================================================
        # add in your other user_input commands
        # =============================================================
        if user_input.lower() == "parse-trs":
            console.print("Within the 'cygnet_input' folder ...")
            console.print("DO NOT TYPE '.csv', just the name of file")
            csv_name = Prompt.ask("Type the filename of the cygnet trs CSV file").strip()
            trs_summary = runParseTRS(csv_name)
            display_trs_summary(trs_summary)
            continue

        if user_input.lower() == "parse-pnt":
            console.print("Within the 'cygnet_input' folder ...")
            console.print("DO NOT TYPE '.csv', just the name of file")
            csv_name = Prompt.ask("Type the filename of the cygnet trs CSV file").strip()
            pnt_summary = runParsePNT(csv_name)
            console.print(pnt_summary)
            continue
        
        if user_input.lower() == "analyze-trs_pnt":

            continue

        else:
            console.print(f"[red]Unknown command: [/red] {user_input!r}\n")

    console.print(Rule(style="dim"))
    console.print(
        Panel.fit("[bold green]take care\n\n          o7 [/bold green]")
    )

# ---------------------------
# Entry Point
# ---------------------------
if __name__ == "__main__":
    main()