import os
import csv
import json
from pathlib import Path
from typing import Any, List, Dict, Optional, Iterable, Set, Tuple

from cyg_to_ign.Scripts import common

def load_workingJSON(path: str) -> Dict[str, Any]:
    # load the entire summaries.json (or {} if missing/corrupt). 
    # safe read; never throws.
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_workingJSON(path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path) # atomic replace
        return {"ok": True, "path": path, "message": "working.json updated atomically."}
    except OSError as e:
        return {"ok": False, "path": path, "message": f"Failed to save working.json: {e}"}

def getParserFilePaths(workingJSON: Dict[str, Any]) -> Dict[str, Any]: 
    parser_filepaths = workingJSON["parser_filepaths"]
    return parser_filepaths

def updateParserFilePath(workingJSON: Dict[str, Any], parserType: str, filepath: str) -> None:
    if "parser_filepaths" not in workingJSON or not isinstance(workingJSON["parser_filepaths"], dict):
        workingJSON["parser_filepaths"] = {}
    
    workingJSON["parser_filepaths"][parserType] = filepath
    return