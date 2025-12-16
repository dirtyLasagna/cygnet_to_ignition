# path
from pathlib import Path

# rich library
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.rule import Rule

# cyg_to_ign imports
from cyg_to_ign.Scripts import common
from cyg_to_ign.Scripts import parse

# parse functions
from cyg_to_ign.Scripts.parse_trs import runParseTRS
from cyg_to_ign.Scripts.parse_pnt import runParsePNT
from cyg_to_ign.Scripts.parse_fac import runParseFAC
from cyg_to_ign.Scripts.compare_trs_pnt import compare_trs_pnt

# command handlers
from cyg_to_ign.Scripts.command_handlers import (
    handle_parse_command,
    handle_compare_command,
    handle_show_cache,
    handle_show_parse_paths
)

# validation utilities
from cyg_to_ign.Scripts.validation_utils import (
    validate_cross_dataset,
    analyze_value_overlap,
    validate_referential_integrity,
    check_site_service_consistency,
    create_merged_validation_dataset
)
from cyg_to_ign.Scripts.summary_utils import load_summaries

# working imports 
from working import cache

# rich formatting
from cyg_to_ign.Scripts.rich_formatting import display_trs_summary, display_pnt_summary, display_fac_summary

# metadata - globals
working_folder = common.getWorkingFolder()
workingJSON_path = working_folder + "\\working.json"
workingJSON = cache.load_workingJSON(workingJSON_path)

inputs_folder_path = common.getCygnetInputFolder()
cygnet_input_csv_filenames = common.getFilesList(inputs_folder_path, [".csv"])
summaries_path = common.getSummaryPath()
console = Console()

parser_filepaths = cache.getParserFilePaths(workingJSON)

# Command registry for help menu
COMMANDS = {
    "test": "Always testing --> experiment with code snippets",
    "parse-trs": "Parse TRS (Table Ref) CSV file",
    "parse-pnt": "Parse PNT (Point) CSV file",
    "parse-fac": "Parse FAC (Facility) CSV file",
    "compare-trs-pnt": "Compare TRS and PNT summaries for coverage analysis",
    "validate-all": "Validate relationships across TRS, PNT, and FAC datasets",
    "show-cache": "Display all cached summaries with timestamps",
    "show-parse-paths": "Show current parser file paths from working.json",
    "help": "Show this help message",
    "q, exit, quit": "Exit the CLI tool"
}

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
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #     === USER - INPUT ===
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            user_input = Prompt.ask("[bold blue]>>>[/bold blue]").strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]Input cancelled (Ctrl+C). Type 'exit' or 'q' to quit.[/yellow]")
            continue

        # =============================
        #       test 
        # =============================
        if user_input.lower() == "test":
            # --- TEST VALIDATION FUNCTIONS HERE ---
            console.print("[bold cyan]Testing Validation Functions[/bold cyan]\n")
            
            # Build filepaths dict from parser_filepaths
            filepaths = {
                "trs": parser_filepaths["base-path"] + "\\" + parser_filepaths.get("parse-trs", "") + parser_filepaths.get("extension", ""),
                "pnt": parser_filepaths["base-path"] + "\\" + parser_filepaths.get("parse-pnt", "") + parser_filepaths.get("extension", ""),
                "fac": parser_filepaths["base-path"] + "\\" + parser_filepaths.get("parse-fac", "") + parser_filepaths.get("extension", "")
            }
            
            console.print("[yellow]File paths:[/yellow]")
            for key, path in filepaths.items():
                console.print(f"  {key}: {path}")
            
            # Test 1: Value Overlap (TRS ENTRY vs PNT uniformdatacode)
            console.print("\n[bold green]Test 1: TRS.ENTRY ↔ PNT.uniformdatacode overlap[/bold green]")
            try:
                overlap = analyze_value_overlap(
                    dataset_a="trs",
                    column_a="ENTRY",
                    dataset_b="pnt",
                    column_b="uniformdatacode",
                    filepaths=filepaths,
                    normalize=True,
                    filter_condition={"dataset": "trs", "column": "TABLE", "value": "~UDCALL"}
                )
                console.print(f"  TRS UDC entries: {overlap['total_a']}")
                console.print(f"  PNT UDC codes: {overlap['total_b']}")
                console.print(f"  Matches: {overlap['intersection']}")
                console.print(f"  PNT coverage: {overlap['overlap_pct_b']}%")
                console.print(f"  Sample missing in PNT: {overlap['sample_only_b'][:5]}")
            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
            
            # Test 2: Referential Integrity (PNT.facilityid -> FAC.id)
            console.print("\n[bold green]Test 2: PNT.facilityid → FAC.id integrity[/bold green]")
            try:
                integrity = validate_referential_integrity(
                    parent_dataset="fac",
                    parent_column="id",
                    child_dataset="pnt",
                    child_column="facilityid",
                    filepaths=filepaths
                )
                console.print(f"  FAC facilities: {integrity['parent_unique_count']}")
                console.print(f"  PNT unique facilities: {integrity['total_child_unique']}")
                console.print(f"  Matched: {integrity['matched_count']}")
                console.print(f"  Orphaned: {integrity['orphaned_count']}")
                console.print(f"  Integrity: {integrity['integrity_pct']}%")
                if integrity['orphan_frequency']:
                    console.print(f"  Top orphans: {list(integrity['orphan_frequency'].items())[:3]}")
            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
            
            continue

        # =============================
        #       quit 
        # =============================
        if user_input.lower() in {"q", "exit", "quit"}:
            console.print("[bold red]Exiting CLI...[/bold red]")
            break
        
        # =============================
        #       help 
        # =============================
        elif user_input == "help":
            console.print("\n[bold cyan]Available commands:[/bold cyan]\n")
            for cmd, description in COMMANDS.items():
                # Calculate tab spacing based on command length
                tab = "\t\t"
                cmd_length = len(cmd)
                tab_count = 2 if cmd_length < 12 else 1
                if tab_count != 2:
                    tab = "\t"
                
                console.print(f" • [yellow]{cmd}[/yellow] {tab}— {description}")
            console.print()
            continue

        
        # =============================
        #       show commands 
        # =============================
        if user_input.lower() == "show-cache":
            handle_show_cache(console)
            continue

        if user_input.lower() == "show-parse-paths":
            handle_show_parse_paths(console, parser_filepaths)
            continue


        # ==================================
        #       parse commands
        # ==================================
        if user_input.lower() == "parse-trs":
            handle_parse_command(
                console, "trs", runParseTRS, display_trs_summary,
                parser_filepaths, workingJSON, workingJSON_path
            )
            continue

        if user_input.lower() == "parse-pnt":
            handle_parse_command(
                console, "pnt", runParsePNT, display_pnt_summary,
                parser_filepaths, workingJSON, workingJSON_path
            )
            continue

        if user_input.lower() == "parse-fac":
            handle_parse_command(
                console, "fac", runParseFAC, display_fac_summary,
                parser_filepaths, workingJSON, workingJSON_path
            )
            continue
        

        # ==================================
        #       compare commands
        # ==================================
        if user_input.lower() == "compare-trs-pnt":
            # Wrapper function to match handler signature
            def compare_wrapper(summaries: dict, filepaths: dict) -> dict:
                return compare_trs_pnt(
                    summaries["trs_summary"],
                    summaries["pnt_summary"],
                    filepaths["trs"],
                    filepaths["pnt"]
                )
            
            handle_compare_command(
                console=console,
                required_summaries=["trs_summary", "pnt_summary"],
                compare_func=compare_wrapper,
                parser_filepaths=parser_filepaths,
                result_label="compare_trs_pnt",
                display_results=True
            )
            continue
        
        # ==================================
        #       validation commands
        # ==================================
        if user_input.lower() == "validate-all":
            console.print("[bold cyan]Starting Cross-Dataset Validation[/bold cyan]\n")
            
            # Check prerequisites - need all three summaries
            required = ["trs_summary", "pnt_summary", "fac_summary"]
            from cyg_to_ign.Scripts.summary_utils import check_summaries
            status = check_summaries(required)
            
            if not status["ok"]:
                console.print("[bold red]Missing required summaries:[/bold red]")
                for lbl in required:
                    s = status["details"][lbl]
                    mark = "[red]✗[/red]" if not s["present"] else "[green]✓[/green]"
                    console.print(f"  {mark} {lbl}")
                console.print("\n[yellow]Please run all parse commands first:[/yellow]")
                console.print("  • parse-trs")
                console.print("  • parse-pnt")
                console.print("  • parse-fac")
                continue
            
            # Load summaries
            cached_summaries = load_summaries()
            trs_summary = cached_summaries.get("trs_summary", {})
            pnt_summary = cached_summaries.get("pnt_summary", {})
            fac_summary = cached_summaries.get("fac_summary", {})
            
            # Build file paths
            trs_filepath = parser_filepaths["base-path"] + "\\\\" + parser_filepaths["parse-trs"] + parser_filepaths.get("extension")
            pnt_filepath = parser_filepaths["base-path"] + "\\\\" + parser_filepaths["parse-pnt"] + parser_filepaths.get("extension")
            fac_filepath = parser_filepaths["base-path"] + "\\\\" + parser_filepaths["parse-fac"] + parser_filepaths.get("extension")
            
            console.print("[cyan]Running validation checks...[/cyan]")
            
            # Run validation
            try:
                validation_results = validate_cross_dataset(
                    trs_summary=trs_summary,
                    pnt_summary=pnt_summary,
                    fac_summary=fac_summary,
                    trs_filepath=trs_filepath,
                    pnt_filepath=pnt_filepath,
                    fac_filepath=fac_filepath
                )
                
                # Display results
                console.print("\n[bold green]Validation Complete![/bold green]\n")
                
                # Summary stats
                console.print("[bold cyan]Dataset Summary:[/bold cyan]")
                summary = validation_results.get("summary", {})
                console.print(f"  TRS rows: {summary.get('trs_total_rows', 0)}")
                console.print(f"  PNT rows: {summary.get('pnt_total_rows', 0)}")
                console.print(f"  FAC rows: {summary.get('fac_total_rows', 0)}")
                
                # TRS-PNT relationship
                console.print("\n[bold cyan]TRS ↔ PNT Relationship:[/bold cyan]")
                trs_pnt = validation_results.get("trs_pnt_relationship", {})
                overlap = trs_pnt.get("overlap", {})
                console.print(f"  Join: {trs_pnt.get('join_description', 'N/A')}")
                console.print(f"  TRS UDC entries: {overlap.get('total_a', 0)}")
                console.print(f"  PNT UDC codes: {overlap.get('total_b', 0)}")
                console.print(f"  Matches: {overlap.get('intersection', 0)}")
                console.print(f"  PNT coverage: {overlap.get('overlap_pct_b', 0)}%")
                
                # PNT-FAC relationship
                console.print("\n[bold cyan]PNT ↔ FAC Relationship:[/bold cyan]")
                pnt_fac = validation_results.get("pnt_fac_relationship", {})
                integrity = pnt_fac.get("referential_integrity", {})
                console.print(f"  Join: {pnt_fac.get('join_description', 'N/A')}")
                console.print(f"  FAC facilities: {integrity.get('parent_unique_count', 0)}")
                console.print(f"  PNT facilities: {integrity.get('total_child_unique', 0)}")
                console.print(f"  Matched: {integrity.get('matched_count', 0)}")
                console.print(f"  Orphaned: {integrity.get('orphaned_count', 0)}")
                console.print(f"  Integrity: {integrity.get('integrity_pct', 0)}%")
                
                # Service consistency
                console.print("\n[bold cyan]Service Consistency:[/bold cyan]")
                service = validation_results.get("service_consistency", {})
                console.print(f"  Joined records: {service.get('total_joined_records', 0)}")
                console.print(f"  Service matches: {service.get('service_matches', 0)}")
                console.print(f"  Service mismatches: {service.get('service_mismatches', 0)}")
                console.print(f"  Mismatch rate: {service.get('service_mismatch_pct', 0)}%")
                
                # Recommendations
                console.print("\n[bold cyan]Recommendations:[/bold cyan]")
                for rec in validation_results.get("recommendations", []):
                    console.print(f"  {rec}")
                
                # Overall status
                status = validation_results.get("validation_status", "UNKNOWN")
                if status == "PASS":
                    console.print(f"\n[bold green]Overall Status: {status}[/bold green]")
                else:
                    console.print(f"\n[bold yellow]Overall Status: {status}[/bold yellow]")
                
                # Save validation summary to summaries.json
                from cyg_to_ign.Scripts.summary_utils import save_summary
                res = save_summary(validation_results, filepath=None, label="validation_all")
                if res.get("ok"):
                    console.print(f"\n[green]✓ Validation results saved to {res['path']}[/green]")
                
                # Create and save merged dataset
                console.print("\n[cyan]Creating merged validation dataset...[/cyan]")
                analytical_folder = common.getRootFolder() + "\\analytical_output"
                merged_output_path = analytical_folder + "\\merged_validation_dataset.csv"
                
                merge_result = create_merged_validation_dataset(
                    trs_filepath=trs_filepath,
                    pnt_filepath=pnt_filepath,
                    fac_filepath=fac_filepath,
                    output_path=merged_output_path
                )
                
                if merge_result.get("success"):
                    console.print(f"[green]✓ Merged dataset created:[/green]")
                    console.print(f"  Rows: {merge_result['row_count']}")
                    console.print(f"  Columns: {merge_result['column_count']}")
                    console.print(f"  Path: {merge_result['output_path']}")
                    
                    # Display merge statistics
                    stats = merge_result['merge_stats']
                    console.print(f"\n[cyan]Merge Statistics:[/cyan]")
                    console.print(f"  TRS (filtered to ~UDCALL): {stats['trs_filtered_rows']}")
                    console.print(f"  TRS→PNT matched: {stats['trs_pnt_matched']}")
                    console.print(f"  TRS→PNT unmatched: {stats['trs_pnt_unmatched']}")
                    
                    # Show count of unmatched TRS entries if any
                    if stats.get('unmatched_trs_count', 0) > 0:
                        console.print(f"[yellow]  ⚠ ~UDCALL Entries without a PNT uniformdatacode match: {stats['unmatched_trs_count']}[/yellow]")
                    
                    console.print(f"\n[cyan]PNT→FAC Join:[/cyan]")
                    console.print(f"  PNT→FAC matched: {stats['pnt_fac_matched']}")
                    console.print(f"  PNT→FAC unmatched: {stats['pnt_fac_unmatched']}")
                    
                    # Save merged dataset path to working.json
                    cache.updateParserFilePath(workingJSON, "merged-validation-dataset", merged_output_path)
                    cache.save_workingJSON(workingJSON_path, workingJSON)
                    console.print(f"\n[green]✓ Merged dataset path saved to working.json[/green]")
                    
                    # Display column names
                    console.print(f"\n[cyan]Merged Dataset Columns ({merge_result['column_count']}):[/cyan]")
                    for i, col in enumerate(merge_result['columns'], 1):
                        console.print(f"  {i:2}. {col}")
                    
                else:
                    console.print(f"[red]✗ Failed to create merged dataset: {merge_result.get('error')}[/red]")
                    if merge_result.get('traceback'):
                        console.print(f"[dim]{merge_result['traceback']}[/dim]")
                
            except Exception as e:
                console.print(f"\n[bold red]Validation failed:[/bold red] {e}")
                import traceback
                traceback.print_exc()
            
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