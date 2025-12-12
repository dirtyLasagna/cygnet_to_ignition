from typing import Dict, Any, List, Tuple
import re
from collections import Counter, defaultdict
import csv

from cyg_to_ign.Scripts.common import getRootFolder, getSummaryPath

summaries_path = getSummaryPath()

def _prefix(s: str) -> str:
    # Get prefix before first delimiter; fallback to 'UNSPEC' if no delimiter
    if not s:
        return "UNSPEC"
    return re.split(r"[_\.\s/]+", s.strip().upper())

def _tokenize(s: str) -> List[str]:
    # tokenize descriptions for simple overlap logic
    if not s:
        return []
    return re.split(r"[_\.\s/]+", s.strip().upper())

def _dups(seq: List[str]) -> List[Tuple[str, int]]:
    # Return list of (normalized_key, count) where count > 1
    c = Counter(_norm_key(x) for x in seq if x)
    return sorted( [(k, v) for k, v in c.items() if v > 1], key=lambda kv: (-kv[1], kv[0]) )

def _norm_key(s: str) -> str:
    # normalize join keys for reliable comparison
    # - strip, uppercase
    # - collapse whitespace
    # - standardize separators: '-' -> '_' 

    if s is None:
        return ""
    s = s.strip().upper()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("-", "_")
    return s

def _extract_trs_keys(trs_summary: Dict[str, Any]) -> Dict[str, Any]:
    # Extract TRS join keys and maps from the TRS summary
    # Expected keys: 'udcall_entries' and 'udcall_map'

    entries = trs_summary.get("udcall_entries") or []
    if not entries and isinstance(trs_summary.get("udcall_map"), dict):
        entries = list(trs_summary["udcall_map"].keys())
    
    # normalize now for set operations (store raw too for dup reporting)
    entries_norm = { _norm_key(x) for x in entries if x }

    # map may be missing; default to empty dict 
    entry_desc_map = trs_summary.get("udcall_map") or {}

    # normalize keys in map for compare; values kept raw
    entry_desc_map_norm = { _norm_key(k): v for k, v in entry_desc_map.items() }

    return {
        "entries_raw": entries,
        "entries_norm": entries_norm,
        "entry_desc_map": entry_desc_map,
        "entry_desc_map_norm": entry_desc_map_norm
    }

def _extract_pnt_keys(pnt_summary: Dict[str, Any]) -> Dict[str, Any]: 
    # Extract PNT join keys and maps from PNT summary
    # expected keys: 'udc_values' and 'udc_desc_map'

    udcs = pnt_summary.get("udc_values") or []
    if not udcs and isinstance(pnt_summary.get("udc_desc_map"), dict):
        udcs = list(pnt_summary["udc_desc_map"].keys())
    
    udcs_norm = {_norm_key(x) for x in udcs if x}
    
    udc_desc_map = pnt_summary.get("udc_desc_map") or {}
    udc_desc_map_norm = { _norm_key(k): v for k, v in udc_desc_map.items() }

    return {
        "udcs_raw": udcs,
        "udcs_norm": udcs_norm,
        "udc_desc_map": udc_desc_map,
        "udc_desc_map_norm": udc_desc_map_norm
    }

def compare_trs_pnt(trs_summary: dict, pnt_summary: dict, trs_filepath: str, pnt_filepath: str) -> dict:
    # Cross-Reference TRS & PNT summaries

    # output structure goal:  
    #{
    #    "matches": [(ENTRY from TRS, UDC from PNT)],
    #    "missing_in_trs": [list of UDCs],
    #    "missing_in_pnt": [list of ENTRYs],
    #    "prefix_groups": {...},
    #    "summary_stats": {...}
    #}

    # 1. define a small "summary schema"
    # 2. normalize the join keys (TRS ENTRY vs PNT UDC) so comparison are robust.
    # 3. build the comparison in layers:
        # header diff
            # key coverage
                # duplicates / conflicts
                    # naming checks
                        # prefix grouping
                            # summary stats
    
    # --- 1) header difference
    #trs_headers = set(trs_summary.get("Headers", []))
    # pnt_headers = set(pnt_summary.get("Headers", []))
    # headers_diff = {
    #     "trs_only": sorted(list(trs_headers - pnt_headers)),
    #     "pnt_only": sorted(list(pnt_headers - trs_headers)),
    #     "common": sorted(list(trs_headers & pnt_headers))
    # }

    # Extract TRS ~UDCALL entries
    trs_entries_raw = []
    trs_entry_desc_map = {}

    with open(trs_filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("TABLE", "").strip().upper() == "~UDCALL":
                entry = row.get("ENTRY", "").strip()
                desc = row.get("DESCRIPTION", "").strip() if "DESCRIPTION" in row else ""
                if entry:
                    trs_entries_raw.append(entry)
                    trs_entry_desc_map[_norm_key(entry)] = desc
    
    # Extract PNT uniformdatacode values
    pnt_udcs_raw = []
    pnt_udc_desc_map = {}

    with open(pnt_filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader: 
            udc = row.get("uniformdatacode", "").strip()
            desc = row.get("description", "").strip() if "description" in row else ""
            if udc:
                pnt_udcs_raw.append(udc)
                pnt_udc_desc_map[_norm_key(udc)] = desc


    # --- 2) extract normalized keys/maps
    trs_entries_norm = { _norm_key(x) for x in trs_entries_raw }
    pnt_udcs_norm = { _norm_key(x) for x in pnt_udcs_raw }

    # helper: key normalization (critical)
        # trim whitespace
        # uppercase
        # collapse internal whitespace
        # standardize separators (e.g., - -> _ aka hyphen becomes underscore)

    # --- 3) Coverage & Set Operations
    match_keys = sorted(list(trs_entries_norm & pnt_udcs_norm))
    missing_in_trs = sorted(list(pnt_udcs_norm - trs_entries_norm)) # present in PNT, not in TRS
    missing_in_pnt = sorted(list(trs_entries_norm - pnt_udcs_norm)) # present in TRS, not in PNT

    stats = {
        "trs_entry_count": len(trs_entries_norm),
        "pnt_udc_count": len(pnt_udcs_norm),
        "match_count": len(match_keys),
        "trs_coverage_pct": round((len(match_keys) / len(trs_entries_norm) * 100.0), 2) if trs_entries_norm else 0.0,
        "pnt_coverage_pct": round((len(match_keys) / len(pnt_udcs_norm) * 100.0), 2) if pnt_udcs_norm else 0.0,
    }

    coverage = {
        "matches": match_keys,
        "missing_in_trs": missing_in_trs,
        "missing_in_pnt": missing_in_pnt,
        "stats": stats
    }

    # --- 4) duplicates
    dup_trs_entry = _dups(trs_entries_raw)
    dup_pnt_udc = _dups(pnt_udcs_raw)

    # --- 6) naming checks (simple token overlap)
    name_checks = { "exact_desc_match": [], "desc_token_overlap_low": [] }
    for k in match_keys: 
        tdesc = trs_entry_desc_map.get(k, "")
        pdesc = pnt_udc_desc_map.get(k, "")
        if tdesc and pdesc:
            if tdesc == pdesc:
                name_checks["exact_desc_match"].append(k)
            else:
                toks_t = set(_tokenize(tdesc))
                toks_p = set(_tokenize(pdesc))
                overlap = len(toks_t & toks_p) / max(1, len(toks_t | toks_p))
                if overlap < 0.3: # tune threshold as needed
                    name_checks["desc_token_overlap_low"].append({
                        "key": k,
                        "trs_desc": tdesc,
                        "pnt_desc": pdesc,
                        "overlap": round(overlap, 2)
                    })

    # --- 7) Prefix grouping (subsystem insight)
    prefix_groups = defaultdict(
        lambda: 
        {
            "keys": 0, "matches": 0,
            "missing_in_trs": 0, "missing_in_pnt": 0
        })
    
    # all_norm_keys = trs_entries_norm | pnt_udcs_norm
    # for k in all_norm_keys:
    #     px = _prefix(k)
    #     prefix_groups[px]["keys"] += 1
    #     if k in match_keys:
    #         prefix_groups[px]["matches"] += 1
    #     elif k in pnt_udcs_norm and k not in trs_entries_norm:
    #         prefix_groups[px]["missing_in_trs"] += 1
    #     elif k in trs_entries_norm and k not in pnt_udcs_norm:
    #         prefix_groups[px]["missing_in_pnt"] += 1
    
    # --- 8) Roll-up summary stats
    summary_stats = {
        #"total_unique_norm_keys": len(all_norm_keys),
        "prefix_count": len(prefix_groups),
        "dup_trs_entry_count": len(dup_trs_entry),
        "dup_pnt_udc_count": len(dup_pnt_udc),
        "exact_desc_match_count": len(name_checks["exact_desc_match"]),
        "low_overlap_desc_count": len(name_checks["desc_token_overlap_low"])
    }

    combined = {
        "coverage": coverage,
        "name_checks": name_checks,
        "prefix_groups": dict(prefix_groups),
        "summary_stats": summary_stats,
        "_meta": {
            "note": "Comparison Strictly on TRS '~UDCALL' ENTRY vs PNT 'uniformdatacode' column"
        }
    }

    return combined