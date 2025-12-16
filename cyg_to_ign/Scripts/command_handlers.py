from typing import Dict, Any, Callable
from rich.console import Console
from cyg_to_ign.Scripts.summary_utils import check_summaries, save_summary, load_summaries
from working import cache


def handle_parse_command(
    console: Console,
    file_type: str,
    parser_func: Callable,
    display_func: Callable,
    parser_filepaths: Dict[str, Any],
    workingJSON: Dict[str, Any],
    workingJSON_path: str
) -> Dict[str, Any]:
    """
    Generic handler for parse commands (parse-trs, parse-pnt, parse-fac).
    
    Args:
        console: Rich console for output
        file_type: Type of file being parsed ('trs', 'pnt', 'fac')
        parser_func: The parsing function to call
        display_func: The display function for results
        parser_filepaths: Dictionary of parser file paths
        workingJSON: Working JSON data
        workingJSON_path: Path to working.json file
    
    Returns:
        Result dictionary from parse.generic_parse_workflow
    """
    from cyg_to_ign.Scripts import parse
    
    return parse.generic_parse_workflow(
        console=console,
        file_type=file_type,
        parser_func=parser_func,
        display_func=display_func,
        parser_filepaths=parser_filepaths,
        workingJSON=workingJSON,
        workingJSON_path=workingJSON_path
    )


def handle_compare_command(
    console: Console,
    required_summaries: list,
    compare_func: Callable,
    parser_filepaths: Dict[str, Any],
    result_label: str,
    display_results: bool = True
) -> Dict[str, Any]:
    """
    Generic handler for comparison commands.
    
    Args:
        console: Rich console for output
        required_summaries: List of required summary labels (e.g., ['trs_summary', 'pnt_summary'])
        compare_func: The comparison function to call
        parser_filepaths: Dictionary of parser file paths
        result_label: Label to save results under in summaries.json
        display_results: Whether to display summary results to console
    
    Returns:
        Combined comparison results dictionary
    """
    # 1. Check prerequisites
    status = check_summaries(required_summaries)
    if not status["ok"]:
        # Show which are missing with helpful messages
        for lbl in required_summaries:
            s = status["details"][lbl]
            mark = "[red]✗[/red]" if not s["present"] else "[green]✓[/green]"
            console.print(f"{mark} {s['label']} - {s['message']}")
        
        summary_names = "', '".join(required_summaries)
        console.print(f"[bold yellow]Please run the required parse commands first, then try again.[/bold yellow]")
        return {"ok": False, "error": "Missing required summaries"}
    
    # 2. Load summaries from cache
    cached_summaries = load_summaries()
    summaries = {}
    for label in required_summaries:
        summaries[label] = cached_summaries.get(label, {})
        if not isinstance(summaries[label], dict):
            console.print(f"[bold red]Cached summary '{label}' is malformed. Re-run parsing commands.[/bold red]")
            return {"ok": False, "error": f"Malformed summary: {label}"}
    
    # 3. Build filepaths for comparison function
    filepaths = {}
    for label in required_summaries:
        # Extract file type from label (e.g., 'trs_summary' -> 'trs')
        file_type = label.replace('_summary', '')
        key = f"parse-{file_type}"
        if key in parser_filepaths:
            filepath = parser_filepaths["base-path"] + "\\" + parser_filepaths[key] + parser_filepaths.get("extension", "")
            filepaths[file_type] = filepath
    
    # 4. Run comparison function
    try:
        combined = compare_func(summaries, filepaths)
    except Exception as e:
        console.print(f"[bold red]Comparison failed:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}
    
    # 5. Display results if requested
    if display_results and isinstance(combined, dict):
        # Extract key stats based on comparison type
        if "coverage" in combined:
            stats = combined.get("coverage", {}).get("stats", {})
            if stats:
                console.print("\n[bold cyan]Comparison Results:[/bold cyan]")
                for key, value in stats.items():
                    console.print(f"  [green]{key}:[/green] {value}")
        
        # Show coverage details if available
        coverage = combined.get("coverage", {})
        if "missing_in_trs" in coverage:
            miss_trs = coverage.get("missing_in_trs", [])
            miss_pnt = coverage.get("missing_in_pnt", [])
            console.print(f"\n[yellow]Missing in TRS:[/yellow] {len(miss_trs)}")
            console.print(f"[yellow]Missing in PNT:[/yellow] {len(miss_pnt)}")
    
    # 6. Save combined analysis into summaries.json
    res = save_summary(combined, filepath=None, label=result_label)
    if isinstance(res, dict) and res.get("ok"):
        console.print(f"\n[green]✓ Saved comparison results[/green] under '[bold]{res['label']}[/bold]' -> {res['path']}")
    else:
        msg = res.get("message", "Unknown error") if isinstance(res, dict) else "save_summary returned non-dict"
        console.print(f"[bold red]Save failed:[/bold red] {msg}")
    
    combined["save_result"] = res
    return combined


def handle_show_cache(console: Console) -> None:
    """
    Display all cached summaries with timestamps.
    
    Args:
        console: Rich console for output
    """
    cached_summaries = load_summaries()
    index = cached_summaries.get("_index", [])
    
    if not index:
        console.print("[yellow]No cached summaries found.[/yellow]")
        return
    
    console.print("[bold cyan]Cached summaries:[/bold cyan]")
    for label in index:
        tab = "\t\t"
        label_length = len(label)
        meta = cached_summaries.get(label, {}).get("_meta", {})
        lu = meta.get("last_updated", "n/a")
        tab_count = 2 if label_length < 12 else 1
        if tab_count != 2:
            tab = "\t"
        
        console.print(f" • [bold]{label}[/bold] {tab} — last_updated: {lu}")


def handle_show_parse_paths(console: Console, parser_filepaths: Dict[str, Any]) -> None:
    """
    Display current parser file paths from working.json.
    
    Args:
        console: Rich console for output
        parser_filepaths: Dictionary of parser file paths
    """
    console.print("[bold cyan]Current parser filepaths in working.json:[/bold cyan]")
    for k, v in parser_filepaths.items():
        console.print(f" • [bold]{k}[/bold] \t— {v}")
