from rich.prompt import Prompt
from cyg_to_ign.Scripts.summary_utils import save_summary
from working import cache

def generic_parse_workflow( console, file_type, parser_func, display_func, parser_filepaths, workingJSON, workingJSON_path):
    # parse function workflow
        # 1 - Get preloaded filename from cache
        # 2 - Call the parser function
        # 3 - Display results
        # 4 - Update working.json cache
        # 5 - Save to summaries.json

    # 1) Get preloaded filename from cache
    preloaded_filename = parser_filepaths.get(f"parse-{file_type}", "N/A")

    console.print("Within the 'cygnet_input' folder ...")
    console.print("DO NOT TYPE '.csv', just the name of file")
    console.print(f"[bold green]Pre-Loaded File: [/bold green] {preloaded_filename}")

    csv_name = Prompt.ask(f"Type the filename of the cygnet {file_type.upper()} CSV file").strip()

    # 2) Call the parser function
    try: 
        summary = parser_func(csv_name)
    except Exception as e:
        console.print(f"[bold red]Error parsing {file_type.upper()}: {e}[/bold red]")
        return {"ok": False, "error": str(e)}
    
    # Validate 
    if not isinstance(summary, dict):
        console.print(f"[bold red]Parser returned invalid data[/bold red]")
        return {"ok": False, "error": "Invalid summary type"}

    # 3) Display results
    display_func(summary)

    # 4) Update working.json cache
    cache.updateParserFilePath(workingJSON, f"parse-{file_type}", csv_name)
    cache.save_workingJSON(workingJSON_path, workingJSON)

    # 5) Save to summaries.json
    try:
        res = save_summary(summary, csv_name, label=f"{file_type}_summary")
    except Exception as e:
        console.print(f"[bold red]Failed to save summary: {e}[/bold red]")
        return {"ok": False, "error": str(e)}

    if res.get("ok"):
        console.print(f"[bold green]✓ {file_type.upper()} summary saved[/bold green]")
    else:
        console.print(f"[yellow]Warning: {res.get('message')}[/yellow]")

    return res