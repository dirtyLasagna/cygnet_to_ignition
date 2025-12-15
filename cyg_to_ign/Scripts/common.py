import os
import csv
from pathlib import Path
from typing import Any, List, Dict, Optional, Iterable, Set, Tuple

def getRootFolder() -> str:
    root_folder = str(Path(__file__).resolve().parent.parent.parent)
    return root_folder

def getSummaryPath() -> str:
    summaries_path = os.path.join("analytical_output", "summaries.json")
    return summaries_path

def getCygnetInputFolder() -> str:
    input_folder = os.path.join(getRootFolder(), "cygnet_input")
    return input_folder

def getWorkingFolder() -> str:
    working_folder = os.path.join(getRootFolder(), "working")
    return working_folder

def _normalize_exts(extensions: Optional[Iterable[str]]) -> Optional[Set]:
    # Normalize extensions to a lowercase set with leading dots
    # example: ['csv', '.XLSX'] -> {'.csv', '.xlsx'}
    if not extensions:
        return None
    norm = set()
    for e in extensions: 
        if not e:
            continue
        e = str(e).strip().lower()
        if not e:
            continue
        if not e.startswith('.'):
            e = f'.{e}'
        norm.add(e)
    return norm if norm else None

def getFilesList(folder_path: str, extensions: Optional[Iterable[str]] = None) -> Tuple[str, List[str]]:
    # list of files (non-recursive) in the given folder path
        # folder_path: base directory to scan
        # extensions: optional iterable of extensions to include (case-insenitive)
            # if none, iunclude all files.
        
    # returns (base_folder, list[filenames])
    base = Path(folder_path).resolve()
    if not base.exists() or not base.is_dir():
        # Safe default: return empty list if folder missing
        return (str(base), [])
    
    ext_set = _normalize_exts(extensions)

    files: List[str] = []
    for entry in base.iterdir():
        if entry.is_file():
            if ext_set:
                if entry.suffix.lower() not in ext_set:
                    continue
            files.append(entry.name) # return filename relative to base

    files.sort()
    return (base, files)