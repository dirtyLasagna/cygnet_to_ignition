# path
from pathlib import Path

# rich library
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.rule import Rule

# common
from cyg_to_ign.Scripts import common

# parse functions
from cyg_to_ign.Scripts.parse_trs import runParseTRS
from cyg_to_ign.Scripts.parse_pnt import runParsePNT, profilePNTFile
from cyg_to_ign.Scripts.compare_trs_pnt import compare_trs_pnt
from cyg_to_ign.Scripts.summary_utils import check_summary, save_summary, check_summaries, load_summaries, get_metadata_filepath

# working imports 
# from working.working_utils import save_parquet, load_parquet, clear_working, save_work_index, load_work_index
from working import cache

# rich formatting
from cyg_to_ign.Scripts.rich_formatting import display_trs_summary, display_pnt_summary

# metadata - globals
working_folder = common.getWorkingFolder()
workingJSON_path = working_folder + "\\working.json"
workingJSON = cache.load_workingJSON(workingJSON_path)

inputs_folder_path = common.getCygnetInputFolder()
cygnet_input_csv_filenames = common.getFilesList(inputs_folder_path, [".csv"])
summaries_path = common.getSummaryPath()
console = Console()

# TODO Get rid of this filepaths method, AUTOMATE IT to dynamically check summaries.json before while loop starts
parser_filepaths = cache.getParserFilePaths(workingJSON)

# ---------------------------
# Endless Loop:
# ---------------------------
def main():

    console.print(
        Panel.fit("[bold red]Oi, Welcome to the 'Cygnet->To->Ignition' CLI Tool[/bold red]\n")
    )

    # point working cache folders
    # -----------------------------------------------
    cache.updateParserFilePath(workingJSON, "base-path", inputs_folder_path)
    cache.save_workingJSON(workingJSON_path, workingJSON)    


    while True:
        # ~~~~~~~~~~~~~~~~~~~~
        # === USER - INPUT ===
        # ~~~~~~~~~~~~~~~~~~~~
        try:
            user_input = Prompt.ask("[bold blue]>>>[/bold blue]").strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]Input cancelled (Ctrl+C). Type 'exit' or 'q' to quit.[/yellow]")
            continue

        # QUIT
        if user_input.lower() in {"q", "exit", "quit"}:
            console.print("[bold red]Exiting CLI...[/bold red]")
            break
        
        # HELP
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

        # TEST
        if user_input.lower() == "test":
            test = parser_filepaths                     # <--- CHANGE YOUR TEST VARIABLE HERE

            console.print("test: ", test)
            console.print("test type: ", type(test))
            continue
        
        # =============================================================
        # add in your other user_input commands
        # =============================================================
        if user_input.lower() == "parse-trs":
            preloaded_filename = parser_filepaths["parse-trs"]
            console.print("Within the 'cygnet_input' folder ...")
            console.print("DO NOT TYPE '.csv', just the name of file")
            console.print(f"[bold green]Pre-Loaded File: [/bold green] {preloaded_filename}")
            csv_name = Prompt.ask("Type the filename of the cygnet trs CSV file").strip()
            
            # get the trs_summary 
            try:
                trs_summary = runParseTRS(csv_name)
            except Exception as e:
                console.print(f"[bold red]Failed to parse TRS:[/bold red] {e}")
                continue

            # validate summary before display/save
            if not isinstance(trs_summary, dict):
                console.print("[bold red]TRS summary is not a dictionary. Skipping save.[/bold red]")
                continue

            display_trs_summary(trs_summary)
            
            trs_csv_filepath = parser_filepaths["parse-trs"]
            # working.json cache shows No CSV filepath stored
            if trs_csv_filepath == None or trs_csv_filepath == "":
                cache.updateParserFilePath(workingJSON, "parse-trs", csv_name)
                cache.save_workingJSON(workingJSON_path, workingJSON)
            # skip update b/c the csv name matches cache
            elif trs_csv_filepath == csv_name:
                console.print("[bold green]CSV Name matches cache, no update required.[/bold green]")
            # TODO handle when the csv_name != cached filepath

            # Save to summaries.json (cache-like)
            try:
                res = save_summary(trs_summary, filepath=trs_csv_filepath, label="trs_summary")
            except Exception as e:
                console.print(f"[bold red]Save failed with exception:[/bold red] {e}")
                continue

            if not isinstance(res, dict):
                console.print("[bold red]Save failed: save_summary returned a non-dict (None?).[/bold red]")
                continue

            if res.get("ok"):
                console.print(f"[green]Saved TRS Summary[/green] under the label '[bold]{res['label']}[/bold]' -> {res['path']}")
            else:
                console.print(f"[bold red]Save failed:[/bold red] {res.get('message', 'Unknown error')}")
            continue

        if user_input.lower() == "parse-pnt":
            console.print("Within the 'cygnet_input' folder ...")
            console.print("DO NOT TYPE '.csv', just the name of file")
            csv_name = Prompt.ask("Type the filename of the cygnet trs CSV file").strip()
            
            try:
                pnt_summary = runParsePNT(csv_name)
            except Exception as e:
                console.print(f"[bold red]Failed to parse PNT:[/bold red] {e}")
                continue

            # validate summary before display/save
            if not isinstance(pnt_summary, dict):
                console.print("[bold red]PNT summary is not a dictionary. Skipping save.[/bold red]")
                continue

            display_pnt_summary(pnt_summary)
            pnt_filepath = inputs_folder_path + csv_name + ".csv"
            #filepaths["pnt"] = pnt_filepath

            # Save to summaries.json (cache-like)
            try:
                res = save_summary(pnt_summary, filepath=pnt_filepath, label="pnt_summary")
            except Exception as e:
                console.print(f"[bold red]Save failed with exception:[/bold red] {e}")
                continue

            if not isinstance(res, dict):
                console.print("[bold red]Save failed: save_summary returned a non-dict (None?).[/bold red]")
                continue

            if res.get("ok"):
                console.print(f"[green]Saved PNT Summary[/green] under the label '[bold]{res['label']}[/bold]' -> {res['path']}")
            else:
                console.print(f"[bold red]Save failed:[/bold red] {res.get('message', 'Unknown error')}")
            continue
        
        if user_input.lower() == "compare-trs-pnt":
            # 1. Check prerequisites
            required = ["trs_summary", "pnt_summary"]
            status = check_summaries(required)
            if not status["ok"]:
                # Show which are missing with helpful messages
                for lbl in required:
                    s = status["details"][lbl]
                    mark = "[red]✗[/red]" if not s["present"] else "[green]✓[/green]"
                    console.print(f"m{mark} {s['label']} - {s['message']}")
                console.print("[bold yellow]Please run 'parse-trs' and 'parse-pnt' first, then try again.[/bold yellow]")
                continue
            
            # 2. Load summaries from cache
            cached_summaries = load_summaries()
            trs_summary = cached_summaries.get("trs_summary", {})
            pnt_summary = cached_summaries.get("pnt_summary", {})

            # ensure dicts type
            if not isinstance(trs_summary, dict) or not isinstance(pnt_summary, dict):
                console.print("[bold red]Cached summaries malformed. Re-run parsing commands.[/bold red]")
                continue

            # 3. Run combined analysis
            
            #try:
            trs_filepath = parser_filepaths["parse-trs"]
            pnt_filepath = parser_filepaths["parse-pnt"]
            combined = compare_trs_pnt(trs_summary, pnt_summary, trs_filepath, pnt_filepath)
            #except Exception as e:
                #console.print(f"[bold red]Comparison failed:[/bold red] {e}")
                #console.print(Exception)
                #continue

            # 4. Brief summary to CLI (counts only; save full to cache/Excel later)
            stats = combined.get("coverage", {}).get("stats", {})
            match_cnt = stats.get("match_count", 0)
            miss_trs = combined.get("coverage", {}).get("missing_in_trs", [])
            miss_pnt = combined.get("coverage", {}).get("missing_in_pnt", [])
            console.print(f"[bold green]Matches:[/bold green] {match_cnt}")
            console.print(f"[yellow]Missing in TRS:[/yellow] {len(miss_trs)}")
            console.print(f"[yellow]Missing in PNT:[/yellow] {len(miss_pnt)}")

            # 5. Save combined analysis into summaries.json for downstream use
            res = save_summary(combined, filepath=None, label="compare_trs_pnt")
            if isinstance(res, dict) and res.get("ok"):
                console.print(f"[green]Saved combined analysis[/green] under '[bold] {res['label']}[/bold]' -> {res['path']}")
            else:
                msg = res.get("message", "Unknown error") if isinstance(res, dict) else "save_summary returned non-dict"
                console.print(f"[bold red]Save failed:[/bold red] {msg}")

            continue

        # SHOW CACHE 
        # =========================================================================================
        if user_input.lower() == "show-cache":
            cached_summaries = load_summaries()
            index = cached_summaries.get("_index", [])
            console.print("[bold cyan]Cached summaries:[/bold cyan]")
            for label in index:
                meta = cached_summaries.get(label, {}).get("_meta", {})
                lu = meta.get("last_updated", "n/a")
                #rc = meta.get("record_count", "n/a")
                console.print(f" • [bold]{label}[/bold] — last_updated: {lu}") #, record_count: {rc}")
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