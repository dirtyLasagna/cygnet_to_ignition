"""
Validation utilities for cross-dataset analysis and join key discovery.
Used to validate relationships between TRS, PNT, and FAC datasets.

Key Relationships:
- TRS.ENTRY (where TABLE="~UDCALL") ↔ PNT.uniformdatacode
- PNT.facilityid ↔ FAC.id (MOST IMPORTANT)
- PNT.service ↔ FAC.service (should default to "UIS")
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import pandas as pd
import csv
from collections import defaultdict, Counter


# =============================================================================
# JOIN KEY DISCOVERY & VALIDATION
# =============================================================================


def find_potential_join_keys(
    summaries: Dict[str, Dict[str, Any]],
    filepaths: Dict[str, str]
) -> Dict[str, Any]:
    """
    Validate the known join key relationships between datasets.
    
    Key Relationships:
    1. TRS.ENTRY (TABLE="~UDCALL") ↔ PNT.uniformdatacode
    2. PNT.facilityid ↔ FAC.id (MOST IMPORTANT)
    3. PNT.service ↔ FAC.service (should be "UIS")
    
    Returns:
    {
        "trs_to_pnt": {
            "join": "ENTRY ↔ uniformdatacode",
            "overlap_analysis": {...}
        },
        "pnt_to_fac": {
            "join": "facilityid ↔ id",
            "referential_integrity": {...}
        },
        "service_check": {
            "pnt_services": ["UIS", "HSS", ...],
            "fac_services": ["UIS", ...],
            "dominant_service": "UIS"
        }
    }
    """
    results = {}
    
    # 1. TRS.ENTRY (UDCALL) ↔ PNT.uniformdatacode
    if "trs" in filepaths and "pnt" in filepaths:
        trs_udc_overlap = analyze_value_overlap(
            dataset_a="trs",
            column_a="ENTRY",
            dataset_b="pnt",
            column_b="uniformdatacode",
            filepaths=filepaths,
            normalize=True,
            filter_condition={"dataset": "trs", "column": "TABLE", "value": "~UDCALL"}
        )
        results["trs_to_pnt"] = {
            "join": "TRS.ENTRY (TABLE='~UDCALL') ↔ PNT.uniformdatacode",
            "overlap_analysis": trs_udc_overlap
        }
    
    # 2. PNT.facilityid ↔ FAC.id (MOST IMPORTANT)
    if "pnt" in filepaths and "fac" in filepaths:
        fac_integrity = validate_referential_integrity(
            parent_dataset="fac",
            parent_column="id",
            child_dataset="pnt",
            child_column="facilityid",
            filepaths=filepaths
        )
        results["pnt_to_fac"] = {
            "join": "PNT.facilityid ↔ FAC.id",
            "referential_integrity": fac_integrity
        }
    
    # 3. Service analysis (should be UIS)
    if "pnt" in filepaths and "fac" in filepaths:
        service_check = _analyze_service_distribution(filepaths)
        results["service_check"] = service_check
    
    return results


# =============================================================================
# REFERENTIAL INTEGRITY VALIDATION
# =============================================================================

def validate_referential_integrity(
    parent_dataset: str,  # e.g., "fac"
    parent_column: str,   # e.g., "id"
    child_dataset: str,   # e.g., "pnt"
    child_column: str,    # e.g., "facilityid"
    filepaths: Dict[str, str],
    sample_size: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Check if foreign key relationship holds (all child values exist in parent).
    
    SQL equivalent: SELECT COUNT(*) FROM pnt WHERE facilityid NOT IN (SELECT id FROM fac)
    
    Returns:
    {
        "valid": True/False,
        "total_child_records": 45726,
        "total_child_unique": 5500,
        "parent_unique_count": 5620,
        "matched_count": 5400,
        "orphaned_count": 100,
        "orphaned_unique_values": ["FAC123", "FAC456", ...],
        "integrity_pct": 98.2,
        "orphan_frequency": {"FAC123": 15, "FAC456": 8, ...}  # top N
    }
    """
    parent_path = filepaths.get(parent_dataset)
    child_path = filepaths.get(child_dataset)
    
    if not parent_path or not child_path:
        return {"error": "Missing file paths"}
    
    # Load parent values (normalize)
    parent_df = pd.read_csv(parent_path, encoding="utf-8", low_memory=False)
    parent_values = set(parent_df[parent_column].dropna().apply(_normalize_key))
    
    # Load child values (normalize) and track frequency
    child_df = pd.read_csv(child_path, encoding="utf-8", low_memory=False)
    child_series = child_df[child_column].dropna()
    child_normalized = child_series.apply(_normalize_key)
    child_values = set(child_normalized)
    
    # Find orphans
    orphaned_values = child_values - parent_values
    matched_values = child_values & parent_values
    
    # Count frequency of orphans
    orphan_freq = child_normalized[child_normalized.isin(orphaned_values)].value_counts().to_dict()
    
    # Sort by frequency and take top N for sample
    orphan_freq_sorted = sorted(orphan_freq.items(), key=lambda x: -x[1])[:sample_size] if sample_size else list(orphan_freq.items())
    
    integrity_pct = round((len(matched_values) / len(child_values) * 100), 2) if child_values else 100.0
    
    return {
        "valid": len(orphaned_values) == 0,
        "total_child_records": len(child_df),
        "total_child_unique": len(child_values),
        "parent_unique_count": len(parent_values),
        "matched_count": len(matched_values),
        "orphaned_count": len(orphaned_values),
        "orphaned_unique_values": sorted(list(orphaned_values))[:sample_size] if sample_size else sorted(list(orphaned_values)),
        "integrity_pct": integrity_pct,
        "orphan_frequency": dict(orphan_freq_sorted)
    }


def validate_cross_dataset(
    trs_summary: Dict[str, Any],
    pnt_summary: Dict[str, Any],
    fac_summary: Dict[str, Any],
    trs_filepath: str,
    pnt_filepath: str,
    fac_filepath: str
) -> Dict[str, Any]:
    """
    Comprehensive 3-way validation of TRS, PNT, and FAC datasets.
    
    Validates:
    1. TRS.ENTRY (TABLE='~UDCALL') ↔ PNT.uniformdatacode
    2. PNT.facilityid ↔ FAC.id (referential integrity)
    3. PNT.service ↔ FAC.service (consistency)
    
    Returns complete validation report with recommendations.
    """
    filepaths = {
        "trs": trs_filepath,
        "pnt": pnt_filepath,
        "fac": fac_filepath
    }
    
    results = {
        "summary": {
            "trs_total_rows": trs_summary.get("Total Rows", 0),
            "pnt_total_rows": pnt_summary.get("Total Rows", 0),
            "fac_total_rows": fac_summary.get("Total Rows", 0)
        }
    }
    
    # 1. TRS ↔ PNT: UDC overlap analysis
    trs_pnt_overlap = analyze_value_overlap(
        dataset_a="trs",
        column_a="ENTRY",
        dataset_b="pnt",
        column_b="uniformdatacode",
        filepaths=filepaths,
        normalize=True,
        filter_condition={"dataset": "trs", "column": "TABLE", "value": "~UDCALL"}
    )
    results["trs_pnt_relationship"] = {
        "join_description": "TRS.ENTRY (TABLE='~UDCALL') ↔ PNT.uniformdatacode",
        "overlap": trs_pnt_overlap
    }
    
    # 2. PNT ↔ FAC: Referential integrity (facilityid → id)
    pnt_fac_integrity = validate_referential_integrity(
        parent_dataset="fac",
        parent_column="id",
        child_dataset="pnt",
        child_column="facilityid",
        filepaths=filepaths
    )
    results["pnt_fac_relationship"] = {
        "join_description": "PNT.facilityid ↔ FAC.id",
        "referential_integrity": pnt_fac_integrity
    }
    
    # 3. Service consistency check
    service_consistency = check_site_service_consistency(
        pnt_filepath=pnt_filepath,
        fac_filepath=fac_filepath
    )
    results["service_consistency"] = service_consistency
    
    # 4. Generate recommendations
    recommendations = []
    
    # TRS-PNT recommendations
    if trs_pnt_overlap.get("overlap_pct_b", 0) >= 95:
        recommendations.append(f"✓ {trs_pnt_overlap['overlap_pct_b']}% of PNT UDC codes have matching entries in TRS")
    else:
        recommendations.append(f"⚠ Only {trs_pnt_overlap['overlap_pct_b']}% of PNT UDC codes match TRS entries - investigate missing codes")
    
    # PNT-FAC recommendations
    if pnt_fac_integrity.get("integrity_pct", 0) >= 95:
        recommendations.append(f"✓ {pnt_fac_integrity['integrity_pct']}% of PNT tags link to valid FAC records")
    else:
        recommendations.append(f"⚠ Only {pnt_fac_integrity['integrity_pct']}% of PNT tags link to FAC - {pnt_fac_integrity['orphaned_count']} orphaned facilities")
    
    # Service consistency
    if service_consistency.get("service_mismatch_pct", 0) < 5:
        recommendations.append(f"✓ Service consistency is good ({service_consistency['service_matches']} matches, {service_consistency['service_mismatches']} mismatches)")
    else:
        recommendations.append(f"⚠ {service_consistency['service_mismatches']} records have mismatched services between PNT and FAC")
    
    results["recommendations"] = recommendations
    results["validation_status"] = "PASS" if all("✓" in r for r in recommendations) else "WARNINGS"
    
    return results


# =============================================================================
# VALUE OVERLAP ANALYSIS
# =============================================================================

def analyze_value_overlap(
    dataset_a: str,
    column_a: str,
    dataset_b: str,
    column_b: str,
    filepaths: Dict[str, str],
    normalize: bool = True,
    filter_condition: Optional[Dict[str, str]] = None,
    sample_size: int = 10
) -> Dict[str, Any]:
    """
    Analyze value overlap between two columns across datasets.
    
    Perfect for: TRS.ENTRY (TABLE='~UDCALL') vs PNT.uniformdatacode
    
    Args:
        filter_condition: Optional filter like {"dataset": "trs", "column": "TABLE", "value": "~UDCALL"}
        sample_size: Number of sample values to return for each category
    
    Returns:
    {
        "dataset_a": "trs.ENTRY",
        "dataset_b": "pnt.uniformdatacode",
        "total_a": 3156,
        "total_b": 453,
        "intersection": 450,
        "overlap_pct_a": 14.3,  # 450/3156 (what % of TRS is in PNT)
        "overlap_pct_b": 99.3,  # 450/453 (what % of PNT is in TRS)
        "only_in_a": 2706,  # count
        "only_in_b": 3,     # count
        "sample_only_a": ["OLD_CODE_1", "OLD_CODE_2", ...],
        "sample_only_b": ["AI_NEW", "DO_SPECIAL", "TI_CUSTOM"],
        "sample_matches": ["AI_CALC", "DI_STATUS", "PRESS_LINE"]
    }
    """
    path_a = filepaths.get(dataset_a)
    path_b = filepaths.get(dataset_b)
    
    if not path_a or not path_b:
        return {"error": "Missing file paths"}
    
    # Load dataset A
    df_a = pd.read_csv(path_a, encoding="utf-8", low_memory=False)
    
    # Apply filter if specified (e.g., TABLE='~UDCALL')
    if filter_condition and filter_condition.get("dataset") == dataset_a:
        filter_col = filter_condition.get("column")
        filter_val = filter_condition.get("value")
        df_a = df_a[df_a[filter_col] == filter_val]
    
    # Extract and normalize values
    values_a = df_a[column_a].dropna()
    if normalize:
        values_a = values_a.apply(_normalize_key)
    set_a = set(values_a)
    
    # Load dataset B
    df_b = pd.read_csv(path_b, encoding="utf-8", low_memory=False)
    values_b = df_b[column_b].dropna()
    if normalize:
        values_b = values_b.apply(_normalize_key)
    set_b = set(values_b)
    
    # Calculate overlap
    intersection = set_a & set_b
    only_a = set_a - set_b
    only_b = set_b - set_a
    
    return {
        "dataset_a": f"{dataset_a}.{column_a}",
        "dataset_b": f"{dataset_b}.{column_b}",
        "total_a": len(set_a),
        "total_b": len(set_b),
        "intersection": len(intersection),
        "overlap_pct_a": round(len(intersection) / len(set_a) * 100, 2) if set_a else 0,
        "overlap_pct_b": round(len(intersection) / len(set_b) * 100, 2) if set_b else 0,
        "only_in_a": len(only_a),
        "only_in_b": len(only_b),
        "sample_only_a": sorted(list(only_a))[:sample_size],
        "sample_only_b": sorted(list(only_b))[:sample_size],
        "sample_matches": sorted(list(intersection))[:sample_size]
    }


# =============================================================================
# DATA CONSISTENCY CHECKS
# =============================================================================

def check_site_service_consistency(
    pnt_filepath: str,
    fac_filepath: str,
    sample_size: int = 10
) -> Dict[str, Any]:
    """
    Validate PNT and FAC have consistent service values for same facilityid.
    (Site is assumed to be the same, so we focus on service)
    
    Returns:
    {
        "total_joined_records": 44926,
        "service_matches": 44700,
        "service_mismatches": 226,
        "service_mismatch_pct": 0.5,
        "mismatch_examples": [
            {
                "facilityid": "FAC123",
                "pnt_service": "UIS",
                "fac_service": "HSS"
            }
        ],
        "service_distribution": {
            "pnt": {"UIS": 45000, "HSS": 700},
            "fac": {"UIS": 5500, "HSS": 120}
        }
    }
    """
    # Load both datasets
    pnt_df = pd.read_csv(pnt_filepath, encoding="utf-8", low_memory=False)
    fac_df = pd.read_csv(fac_filepath, encoding="utf-8", low_memory=False)
    
    # Normalize join keys
    pnt_df["_facilityid_norm"] = pnt_df["facilityid"].apply(_normalize_key)
    fac_df["_id_norm"] = fac_df["id"].apply(_normalize_key)
    
    # Merge on facilityid ↔ id
    merged = pnt_df.merge(
        fac_df,
        left_on="_facilityid_norm",
        right_on="_id_norm",
        how="inner",
        suffixes=("_pnt", "_fac")
    )
    
    # Compare service columns
    merged["service_match"] = (
        merged["service_pnt"].fillna("").str.upper() == 
        merged["service_fac"].fillna("").str.upper()
    )
    
    service_matches = merged["service_match"].sum()
    service_mismatches = (~merged["service_match"]).sum()
    
    # Get mismatch examples
    mismatch_df = merged[~merged["service_match"]]
    mismatch_examples = []
    for _, row in mismatch_df.head(sample_size).iterrows():
        mismatch_examples.append({
            "facilityid": row["facilityid"],
            "pnt_service": row["service_pnt"],
            "fac_service": row["service_fac"]
        })
    
    # Service distribution
    pnt_service_dist = pnt_df["service"].value_counts().to_dict()
    fac_service_dist = fac_df["service"].value_counts().to_dict()
    
    return {
        "total_joined_records": len(merged),
        "service_matches": int(service_matches),
        "service_mismatches": int(service_mismatches),
        "service_mismatch_pct": round((service_mismatches / len(merged) * 100), 2) if len(merged) > 0 else 0,
        "mismatch_examples": mismatch_examples,
        "service_distribution": {
            "pnt": pnt_service_dist,
            "fac": fac_service_dist
        }
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_key(value: str) -> str:
    """Normalize a value for comparison (uppercase, strip, replace hyphen with underscore)"""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper().replace("-", "_")


def create_merged_validation_dataset(
    trs_filepath: str,
    pnt_filepath: str,
    fac_filepath: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a focused merged dataset with only essential columns: TRS → PNT → FAC
    
    Selected Columns:
    - TRS (2): ENTRY, DESC (from TABLE='~UDCALL')
    - PNT (9): uniformdatacode, description, longdescription, units, pointdatatype, 
               site, service, taglong, facilityid
    - FAC (9): id, site, service, is_active, type, desc, category, info0, info1
    
    Final Column Order (20 columns):
    [TRS] ENTRY → [PNT] uniformdatacode → [TRS] DESC → [PNT] description → 
    [PNT] longdescription → [PNT] units → [PNT] pointdatatype → [PNT] site → 
    [FAC] site → [PNT] service → [FAC] service → [PNT] taglong → [PNT] facilityid → 
    [FAC] id → [FAC] is_active → [FAC] type → [FAC] category → [FAC] desc → 
    [FAC] info0 → [FAC] info1
    
    Merge Strategy:
    1. Filter TRS to TABLE='~UDCALL' and select ENTRY, DESC
    2. Merge TRS → PNT on (ENTRY = uniformdatacode) using inner join
       - Drops unmatched TRS entries (tracked separately)
    3. Merge Result → FAC on (facilityid = id) using left join
    
    Returns:
    {
        "success": True,
        "merged_df": DataFrame,
        "output_path": "path/to/merged.csv",
        "row_count": 3150,
        "column_count": 20,
        "columns": ["trs_entry", "pnt_uniformdatacode", ...],
        "merge_stats": {
            "trs_filtered_rows": 3157,
            "trs_pnt_matched": 3150,
            "trs_pnt_unmatched": 7,
            "unmatched_trs_entries": ["UDC123", "UDC456", ...],
            "pnt_fac_matched": 3100,
            "pnt_fac_unmatched": 50
        }
    }
    """
    try:
        # 1. Load TRS and filter to ~UDCALL, select only ENTRY and DESC
        trs_df = pd.read_csv(trs_filepath, encoding="utf-8", low_memory=False)
        trs_udcall = trs_df[trs_df["TABLE"].str.upper() == "~UDCALL"][["ENTRY", "DESC"]].copy()
        trs_filtered_rows = len(trs_udcall)
        
        # Normalize TRS.ENTRY for matching
        trs_udcall["_entry_norm"] = trs_udcall["ENTRY"].apply(_normalize_key)
        
        # 2. Load PNT, select only needed columns
        pnt_df = pd.read_csv(pnt_filepath, encoding="utf-8", low_memory=False)
        pnt_columns = ["uniformdatacode", "description", "longdescription", "units", 
                      "pointdatatype", "site", "service", "taglong", "facilityid"]
        pnt_df = pnt_df[pnt_columns].copy()
        
        # Normalize PNT columns for matching
        pnt_df["_udc_norm"] = pnt_df["uniformdatacode"].apply(_normalize_key)
        pnt_df["_facilityid_norm"] = pnt_df["facilityid"].apply(_normalize_key)
        
        # 3. Merge TRS → PNT (INNER join to drop unmatched TRS)
        merged = trs_udcall.merge(
            pnt_df,
            left_on="_entry_norm",
            right_on="_udc_norm",
            how="inner",  # Only keep matched rows
            suffixes=("_trs", "_pnt")
        )
        
        trs_pnt_matched = len(merged)
        trs_pnt_unmatched = trs_filtered_rows - trs_pnt_matched
        
        # Track unmatched TRS entries
        matched_entries = set(merged["_entry_norm"])
        all_entries = set(trs_udcall["_entry_norm"])
        unmatched_entries = all_entries - matched_entries
        unmatched_trs_original = trs_udcall[trs_udcall["_entry_norm"].isin(unmatched_entries)]["ENTRY"].tolist()
        
        # 4. Load FAC, select only needed columns
        fac_df = pd.read_csv(fac_filepath, encoding="utf-8", low_memory=False)
        fac_columns = ["id", "site", "service", "is_active", "type", "desc", 
                      "category", "info0", "info1"]
        fac_df = fac_df[fac_columns].copy()
        fac_df["_id_norm"] = fac_df["id"].apply(_normalize_key)
        
        # 5. Merge (TRS+PNT) → FAC (LEFT join to keep all PNT records)
        merged = merged.merge(
            fac_df,
            left_on="_facilityid_norm",
            right_on="_id_norm",
            how="left",
            suffixes=("_pnt", "_fac")
        )
        
        pnt_fac_matched = merged["id"].notna().sum()
        pnt_fac_unmatched = len(merged) - pnt_fac_matched
        
        # 6. Reorder columns to specified order and rename with prefixes
        final_columns = [
            ("trs_entry", "ENTRY"),
            ("pnt_uniformdatacode", "uniformdatacode"),
            ("trs_desc", "DESC"),
            ("pnt_description", "description"),
            ("pnt_longdescription", "longdescription"),
            ("pnt_units", "units"),
            ("pnt_pointdatatype", "pointdatatype"),
            ("pnt_site", "site_pnt"),
            ("fac_site", "site_fac"),
            ("pnt_service", "service_pnt"),
            ("fac_service", "service_fac"),
            ("pnt_taglong", "taglong"),
            ("pnt_facilityid", "facilityid"),
            ("fac_id", "id"),
            ("fac_is_active", "is_active"),
            ("fac_type", "type"),
            ("fac_category", "category"),
            ("fac_desc", "desc"),
            ("fac_info0", "info0"),
            ("fac_info1", "info1")
        ]
        
        # Build final dataframe with renamed columns
        final_df = pd.DataFrame()
        for new_name, old_name in final_columns:
            if old_name in merged.columns:
                final_df[new_name] = merged[old_name]
            else:
                # Handle cases where column might not exist
                final_df[new_name] = None
        
        # Save if output_path provided
        if output_path:
            final_df.to_csv(output_path, index=False, encoding="utf-8")
        
        return {
            "success": True,
            "merged_df": final_df,
            "output_path": output_path,
            "row_count": len(final_df),
            "column_count": len(final_df.columns),
            "columns": list(final_df.columns),
            "merge_stats": {
                "trs_filtered_rows": int(trs_filtered_rows),
                "trs_pnt_matched": int(trs_pnt_matched),
                "trs_pnt_unmatched": int(trs_pnt_unmatched),
                "unmatched_trs_count": len(unmatched_trs_original),
                "pnt_fac_matched": int(pnt_fac_matched),
                "pnt_fac_unmatched": int(pnt_fac_unmatched),
                "final_row_count": len(final_df)
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "merged_df": None
        }


def _analyze_service_distribution(filepaths: Dict[str, str]) -> Dict[str, Any]:
    """Analyze service column distribution in PNT and FAC datasets."""
    pnt_df = pd.read_csv(filepaths["pnt"], encoding="utf-8", low_memory=False)
    fac_df = pd.read_csv(filepaths["fac"], encoding="utf-8", low_memory=False)
    
    pnt_services = pnt_df["service"].value_counts().to_dict()
    fac_services = fac_df["service"].value_counts().to_dict()
    
    # Find dominant service
    dominant_pnt = max(pnt_services, key=pnt_services.get) if pnt_services else "N/A"
    dominant_fac = max(fac_services, key=fac_services.get) if fac_services else "N/A"
    
    return {
        "pnt_services": pnt_services,
        "fac_services": fac_services,
        "dominant_service_pnt": dominant_pnt,
        "dominant_service_fac": dominant_fac,
        "services_match": dominant_pnt == dominant_fac
    }
