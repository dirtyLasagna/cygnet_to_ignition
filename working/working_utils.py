import os
import json
import pandas as pd
from typing import Dict, Any, Optional

# common
from cyg_to_ign.Scripts.common  import getRootFolder

ROOT_PATH = getRootFolder()
WORK_DIR = os.path.join("working")
WORK_INDEX = os.path.join(WORK_DIR, "working.json")

def _ensure_workdir():
    os.makedirs(WORK_DIR, exist_ok=True)

def load_work_index() -> Dict[str, Any]:
    _ensure_workdir()
    if not os.path.exists(WORK_INDEX):
        return {}
    try:
        with open(WORK_INDEX, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}

def save_work_index(index: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_workdir()
    tmp = f"{WORK_INDEX}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    os.replace(tmp, WORK_INDEX)
    return {"ok": True, "path": WORK_INDEX}

def save_parquet(df: pd.DataFrame, filename: str) -> str:
    # save a dataframe to WORK_DIR
    _ensure_workdir()
    path = os.path.join(WORK_DIR, filename)
    df.to_parquet(path, index=False)
    # update index
    idx = load_work_index()
    idx.setdefault("_datasets", {})[filename] = {"rows": int(len(df))}
    save_work_index(idx)
    return path

def load_parquet(filename: str) -> Optional[pd.DataFrame]:
    # load a dataframe from WORK_DIR/filename (Parquet). Returns None if missing
    path = os.path.join(WORK_DIR, filename)
    if not os.path.exists(path):
        return None
    return pd.read_parquet(path)

def clear_working() -> Dict[str, Any]:
    # Clear all working artifacts (careful!). Leaves summaries.json untouched.
    _ensure_workdir()
    try:
        for name in os.listdir(WORK_DIR):
            os.remove(os.path.join(WORK_DIR, name))
        return {"ok": True, "message": "Cleared working store."}
    except OSError as e:
        return {"ok": False, "message": str(e)}

