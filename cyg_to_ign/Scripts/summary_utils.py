# imports
from cyg_to_ign.Scripts.common import getRootFolder, getSummaryPath

# 
import json
import os 
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

path = getRootFolder() + "/analytical_output/summaries.json"
summaries_path = getSummaryPath()

# metadata
inputs_folder_path = getRootFolder() + "\\cygnet_input\\"

def _ensure_output_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def _atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    # Write JSON to temp file first, then replaces
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)

def _load_existing(path: str) -> Dict[str, Any]:
    # Load existing summaries.json if present, else return an empty dict
    if not os.path.exists(path):
        return {}
    try: 
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # If corrupted or unreadable, start fresh but doesn't crash the CLI
        return {}

def save_summary(summ_dict: Dict[str, Any], filepath: Optional[str], label: Optional[str] = None) -> Dict[str, Any]:
    # Saves a summary dictionary into analytical_output/summaries.json
        # Behavior:
            # if 'label' is provided, saves under that key.
            # else, uses `summ_dict.get("_label")` if present.
            # else (default for your first test), saves under "trs_summary".
            # adds metadata: last_updated (ISO), unix_ts, and record_count if available.
        
        # Returns: 
            # A result dict: {"ok": bool, "path": str, "label": str, "message": str}
        
        # Example:
            # From parse_trs
                # result = save_summary(trs_summary) --> defaults to "trs_summary"
            # Or explicitly
                # result = save_summary(trs_summary, label="trs_summary")
        
        result = {"ok": False, "path": summaries_path, "label": None, "message": ""}

        # basic validation
        if not isinstance(summ_dict, dict):
            result["message"] = "summ_dict must be a dict."
            return result
        
        # resolve the label (namespace) to store under
        resolved_label = (
            label
            or summ_dict.get("_label")  # allow caller to embed a label
            or "trs_summary"            # sensible default for initial testing
        )
        result["label"] = resolved_label

        # ensure output directory exists
        _ensure_output_dir(summaries_path)

        # load existing cache
        cache = _load_existing(summaries_path)

        # compute metadata
        iso_now = datetime.now().isoformat(timespec="seconds")
        unix_ts = int(time.time())

        # shallow copy to avoid mutating caller's object 
        payload = dict(summ_dict)

        # attach metadata without clobbering potential user fields 
        meta = payload.get("_meta", {})
        meta.update({
            "last_updated": iso_now,
            "unix_ts": unix_ts,
            "source": meta.get("source", resolved_label),
            "filepath": filepath if filepath == "" else "N/A"
        })
        payload["_meta"] = meta

        # Convenience stat if the summary includes a row count or similar
        if "total_rows" in payload and "_meta" in payload:
            payload["_meta"]["record_count"] = payload.get("total_rows")
        
        # merge into cache under the resolved label
        cache[resolved_label] = payload

        # optional top-level index of what labels exist
        cache["_index"] = sorted([ k for k in cache.keys() if not k.startswith("_") ])

        # Write atomically
        try: 
            _atomic_write_json(summaries_path, cache)
        except OSError as e:
            result["message"] = f"Failed to write summaries.json: {e}"
            return result
        
        result["ok"] = True
        result["message"] = f"Saved summary under '{resolved_label}'."
        return result

def get_metadata_filepath(path: str = summaries_path, label: str = "") -> str:
    summary_dict = load_summaries(summaries_path)
    filepath = summary_dict[label]["_meta"]["filepath"]
    return filepath

def load_summary(path: str = summaries_path) -> Dict[str, Any]:
    return

def load_summaries(path: str = summaries_path) -> Dict[str, Any]:
    # load the entire summaries.json (or {} if missing/corrupt). 
    # safe read; never throws.
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    
def check_summary(label: str, path: str = summaries_path) -> Dict[str, Any]:
    # Check presence and basic status of a single summary in summaries.json

    # Returns:
        # {
        # "label": str, "present": bool, "last_updated": Optional[str], "count": Optional[int], "path": str, "message": str
        # }
    
    cache = load_summaries(path)
    payload = cache.get(label, {})
    present = bool(payload)

    last_updated = None
    count = None
    if present and isinstance(payload, dict):
        meta = payload.get("_meta", {})
        last_updated = meta.get("last_updated")
        count = meta.get("record_count")
    
    message = (
        f"Summary '{label}' is present."
        if present else
        f"Summary '{label}' not found. Please run its parse command first."
    )

    return {
        "label": label,
        "present": present,
        "last_updated": last_updated,
        "count": count,
        "path": path,
        "message": message
    }

def check_summaries(required_labels: List[str], path: str = summaries_path) -> Dict[str, Any]:
    # check a set of required labels at once 
    
    # Returns:
        # {
        # "ok": bool, "path": str, "missing": List[str], "details": Dict[str, Dict]
        # }
    
    details: Dict[str, Any] = {}
    missing: List[str] = []

    for label in required_labels:
        status = check_summary(label, path=path)
        details[label] = status
        if not status["present"]:
            missing.append(label)

    return {
        "ok": len(missing) == 0,
        "path": path,
        "missing": missing,
        "details": details
    } 

def clear_summary():

    return

def clear_summaries(path: str = summaries_path) -> Dict[str, Any]:
    result = {"ok": False, "path": path, "message": ""}
    try: 
        if os.path.exists(path):
            os.remove(path)
        result["ok"] = True
        result["message"] = "Cleared summaries cache."
    except OSError as e:
        result["message"] = f"Failed to clear cache: {e}"

def show_summary():

    return 
