"""
Facility Attribute Analysis - Phase 1: Attribute Profiling

This module analyzes FAC (Facility) attributes to discover natural groupings
and patterns that help identify equipment types without relying on pre-defined
equipment classifications.

Strategy:
1. Leverage existing summary statistics (empty/full/partial columns)
2. Calculate discriminative power of each attribute
3. Discover "attribute signatures" - patterns of which columns are filled
4. Group facilities by similar signatures
5. Extract common patterns within groups

This is designed to work generically across different company Cygnet systems.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import math


# =============================================================================
# PHASE 1: ATTRIBUTE PROFILING
# =============================================================================

def analyze_fac_attributes(
    fac_filepath: str,
    fac_summary: Dict[str, Any],
    output_detail: str = "summary"  # "summary", "detailed", "full"
) -> Dict[str, Any]:
    """
    Comprehensive attribute analysis of FAC dataset.
    
    Args:
        fac_filepath: Path to FAC CSV file
        fac_summary: Pre-computed summary from summaries.json
        output_detail: Level of detail to return
            - "summary": High-level overview
            - "detailed": Include top patterns and examples
            - "full": Complete analysis with all data
    
    Returns:
        {
            "column_profiles": {...},      # Per-column statistics and discriminative power
            "attribute_signatures": {...}, # Groupings based on filled columns
            "key_attributes": [...],       # Most discriminative attributes
            "patterns_discovered": {...},  # Common value patterns
            "facility_groups": {...},      # Natural groupings found
            "recommendations": [...]       # Suggested next steps
        }
    """
    results = {
        "total_facilities": fac_summary.get("Total Rows", 0),
        "total_columns": len(fac_summary.get("Headers", [])),
        "analysis_timestamp": pd.Timestamp.now().isoformat()
    }
    
    # 1. Column Profiling - Calculate discriminative power
    column_profiles = _profile_columns(fac_summary)
    results["column_profiles"] = column_profiles
    
    # 2. Identify key discriminative attributes
    key_attrs = _identify_key_attributes(column_profiles)
    results["key_attributes"] = key_attrs
    
    # 3. Analyze attribute fill patterns (signatures)
    # Load actual FAC data for pattern analysis
    fac_df = pd.read_csv(fac_filepath, encoding="utf-8", low_memory=False)
    signatures = _discover_attribute_signatures(fac_df, key_attrs)
    results["attribute_signatures"] = signatures
    
    # 4. Discover natural facility groups based on signatures
    facility_groups = _group_by_signatures(fac_df, signatures, output_detail)
    results["facility_groups"] = facility_groups
    
    # 5. Analyze common value patterns within key attributes
    patterns = _discover_value_patterns(fac_df, key_attrs, output_detail)
    results["patterns_discovered"] = patterns
    
    # 6. Generate recommendations for next steps
    recommendations = _generate_recommendations(results)
    results["recommendations"] = recommendations
    
    # Trim output based on detail level
    if output_detail == "summary":
        results = _trim_to_summary(results)
    
    return results


# =============================================================================
# COLUMN PROFILING
# =============================================================================

def _profile_columns(fac_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze each column's characteristics using pre-computed summary stats.
    
    Calculates:
    - Fill rate (% non-empty)
    - Unique value count
    - Discriminative score (combination of fill rate and uniqueness)
    - Column category (structural, descriptive, attribute, etc.)
    """
    total_rows = fac_summary.get("Total Rows", 1)
    headers = fac_summary.get("Headers", [])
    non_empty = fac_summary.get("Non Empty Counts Per Column", {})
    unique_counts = fac_summary.get("Unique Counts", {})
    percentage_filled = fac_summary.get("Percentage Filled", {})
    
    profiles = {}
    
    for col in headers:
        # Parse fill count (format: "5408/5620")
        fill_info = non_empty.get(col, "0/0")
        filled_count = int(fill_info.split("/")[0]) if "/" in fill_info else 0
        fill_rate = filled_count / total_rows if total_rows > 0 else 0
        
        # Get unique count
        unique_count = unique_counts.get(col, 0)
        
        # Calculate discriminative power
        # High discrimination = moderate fill rate + high uniqueness
        # We want columns that:
        # - Aren't empty (useless)
        # - Aren't 100% filled with same value (not discriminative)
        # - Have diverse values (high uniqueness)
        
        if fill_rate == 0:
            discriminative_score = 0.0
        elif unique_count <= 1:
            discriminative_score = 0.0
        else:
            # Score combines fill rate and uniqueness ratio
            uniqueness_ratio = unique_count / filled_count if filled_count > 0 else 0
            # Prefer columns with 20-80% fill rate (most discriminative)
            fill_score = 1.0 - abs(fill_rate - 0.5) * 2  # Peak at 50% fill
            # Balance between uniqueness and practical utility
            unique_score = min(uniqueness_ratio * 2, 1.0)  # Cap at 1.0
            discriminative_score = (fill_score * 0.4 + unique_score * 0.6)
        
        # Categorize column type
        category = _categorize_column(col, fill_rate, unique_count, total_rows)
        
        profiles[col] = {
            "fill_rate": round(fill_rate, 4),
            "filled_count": filled_count,
            "unique_count": unique_count,
            "discriminative_score": round(discriminative_score, 4),
            "category": category,
            "uniqueness_ratio": round(unique_count / filled_count, 4) if filled_count > 0 else 0
        }
    
    return profiles


def _categorize_column(col: str, fill_rate: float, unique_count: int, total_rows: int) -> str:
    """Categorize column based on name and characteristics."""
    col_lower = col.lower()
    
    # Structural columns (always present, low uniqueness)
    if col_lower in ["site", "service", "is_active"]:
        return "structural"
    
    # Identity columns (unique per facility)
    if col_lower in ["id"] or unique_count > total_rows * 0.8:
        return "identity"
    
    # Descriptive columns
    if col_lower in ["desc", "type", "category", "info0", "info1"]:
        return "descriptive"
    
    # Attribute columns
    if col_lower.startswith("attr"):
        if fill_rate == 0:
            return "unused_attribute"
        elif fill_rate < 0.1:
            return "rare_attribute"
        elif fill_rate > 0.5:
            return "common_attribute"
        else:
            return "moderate_attribute"
    
    # Table columns
    if col_lower.startswith("table"):
        if fill_rate == 0:
            return "unused_table"
        else:
            return "table_ref"
    
    # Yes/No columns
    if col_lower.startswith("yes_no"):
        return "boolean_flag"
    
    # Comment
    if col_lower == "comment":
        return "comment"
    
    return "other"


# =============================================================================
# KEY ATTRIBUTE IDENTIFICATION
# =============================================================================

def _identify_key_attributes(column_profiles: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Identify the most discriminative attributes for facility grouping.
    
    Returns list of key attributes ranked by discriminative power.
    """
    # Filter to attributes and descriptive columns
    candidates = []
    for col, profile in column_profiles.items():
        category = profile["category"]
        score = profile["discriminative_score"]
        
        # Include descriptive and attribute columns with meaningful scores
        if category in ["descriptive", "common_attribute", "moderate_attribute", "rare_attribute"]:
            if score > 0.1:  # Threshold for consideration
                candidates.append({
                    "column": col,
                    "score": score,
                    "fill_rate": profile["fill_rate"],
                    "unique_count": profile["unique_count"],
                    "category": category
                })
    
    # Sort by discriminative score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    return candidates


# =============================================================================
# ATTRIBUTE SIGNATURE DISCOVERY
# =============================================================================

def _discover_attribute_signatures(
    fac_df: pd.DataFrame,
    key_attrs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Discover patterns of which attributes are filled together.
    
    An "attribute signature" is a pattern like:
    - "type + category + info0 filled, but info1 empty"
    - "attr2 + attr7 + attr27 filled"
    
    This helps identify natural facility groupings.
    Returns facility indices for each pattern for Phase 2 use.
    """
    # Focus on top discriminative columns
    top_n = min(20, len(key_attrs))
    focus_cols = [attr["column"] for attr in key_attrs[:top_n]]
    
    # Create binary presence matrix (1 = filled, 0 = empty/NA)
    presence_matrix = fac_df[focus_cols].notna().astype(int)
    
    # Convert each row to a signature tuple and track indices
    signatures_with_idx = []
    for idx, row in presence_matrix.iterrows():
        sig_tuple = tuple(row.values)
        signatures_with_idx.append((sig_tuple, idx))
    
    # Group facilities by signature
    signature_groups = defaultdict(list)
    for sig_tuple, idx in signatures_with_idx:
        signature_groups[sig_tuple].append(idx)
    
    # Count signature frequencies and get facility info
    signature_patterns = []
    for sig_tuple, indices in sorted(signature_groups.items(), key=lambda x: -len(x[1]))[:50]:
        filled_cols = [focus_cols[i] for i, val in enumerate(sig_tuple) if val == 1]
        empty_cols = [focus_cols[i] for i, val in enumerate(sig_tuple) if val == 0]
        
        # Get ALL facility details (id, desc, type) for Phase 2/3
        facilities = []
        for idx in indices:
            fac_id = str(fac_df.loc[idx, 'id']) if 'id' in fac_df.columns else str(idx)
            fac_desc = str(fac_df.loc[idx, 'desc']) if 'desc' in fac_df.columns else "N/A"
            fac_type = str(fac_df.loc[idx, 'type']) if 'type' in fac_df.columns else "N/A"
            facilities.append({
                "id": fac_id,
                "desc": fac_desc[:100],  # Keep full-ish descriptions
                "type": fac_type
            })
        
        signature_patterns.append({
            "signature_id": hash(sig_tuple),
            "facility_count": len(indices),
            "percent_of_total": round(len(indices) / len(fac_df) * 100, 2),
            "filled_columns": filled_cols,
            "empty_columns": empty_cols,
            "column_fill_count": len(filled_cols),
            "facilities": facilities,  # ALL facilities with id/desc/type
            "sample_facilities": facilities[:5]  # Sample for display
        })
    
    return {
        "total_unique_signatures": len(signature_groups),
        "columns_analyzed": focus_cols,
        "top_patterns": signature_patterns
    }


# =============================================================================
# FACILITY GROUPING
# =============================================================================

def _group_by_signatures(
    fac_df: pd.DataFrame,
    signatures: Dict[str, Any],
    output_detail: str
) -> Dict[str, Any]:
    """
    Group facilities based on their attribute signatures.
    
    This creates natural clusters of similar facilities.
    Now includes facility indices and sample information.
    """
    top_patterns = signatures.get("top_patterns", [])
    
    groups = []
    for i, pattern in enumerate(top_patterns, 1):  # No limit - discover ALL patterns
        group_info = {
            "group_id": i,
            "facility_count": pattern["facility_count"],
            "percent_of_total": pattern["percent_of_total"],
            "key_filled_attributes": pattern["filled_columns"][:10],  # Top 10
            "attribute_count": pattern["column_fill_count"],
            "facilities": pattern["facilities"],  # ALL facilities with id/desc/type
            "sample_facilities": pattern["sample_facilities"]  # Sample for display
        }
        
        groups.append(group_info)
    
    return {
        "total_groups": len(groups),
        "groups": groups,
        "coverage": sum(g["percent_of_total"] for g in groups)
    }


# =============================================================================
# VALUE PATTERN DISCOVERY
# =============================================================================

def _discover_value_patterns(
    fac_df: pd.DataFrame,
    key_attrs: List[Dict[str, Any]],
    output_detail: str
) -> Dict[str, Any]:
    """
    Analyze common values within key attributes.
    
    For example:
    - type column: what are the most common types?
    - category column: what categories exist?
    - attr2: what values appear most often?
    """
    patterns = {}
    
    # Focus on top 10 most discriminative columns
    top_cols = [attr["column"] for attr in key_attrs[:10]]
    
    for col in top_cols:
        if col not in fac_df.columns:
            continue
        
        # Get value counts (excluding NaN)
        value_counts = fac_df[col].value_counts()
        total_filled = value_counts.sum()
        
        # Top values
        top_values = []
        for value, count in value_counts.head(15).items():
            top_values.append({
                "value": str(value),
                "count": int(count),
                "percent": round(count / total_filled * 100, 2) if total_filled > 0 else 0
            })
        
        patterns[col] = {
            "total_unique_values": len(value_counts),
            "total_filled": int(total_filled),
            "top_values": top_values
        }
    
    return patterns


# =============================================================================
# RECOMMENDATIONS
# =============================================================================

def _generate_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate actionable recommendations based on analysis."""
    recommendations = []
    
    key_attrs = results.get("key_attributes", [])
    facility_groups = results.get("facility_groups", {})
    patterns = results.get("patterns_discovered", {})
    
    # Recommendation 1: Key discriminative attributes
    if len(key_attrs) > 0:
        top_3 = [attr["column"] for attr in key_attrs[:3]]
        recommendations.append(
            f"✓ Top discriminative attributes: {', '.join(top_3)}"
        )
    else:
        recommendations.append("⚠ No highly discriminative attributes found")
    
    # Recommendation 2: Natural groupings
    group_count = facility_groups.get("total_groups", 0)
    coverage = facility_groups.get("coverage", 0)
    if group_count > 0:
        recommendations.append(
            f"✓ Discovered {group_count} natural facility groups covering {coverage:.1f}% of facilities"
        )
    
    # Recommendation 3: Type/Category analysis
    if "type" in patterns:
        type_diversity = patterns["type"]["total_unique_values"]
        recommendations.append(
            f"✓ Found {type_diversity} unique facility types - good starting point for classification"
        )
    
    if "category" in patterns:
        cat_diversity = patterns["category"]["total_unique_values"]
        if cat_diversity < 10:
            recommendations.append(
                f"✓ Category field has {cat_diversity} values - useful for high-level grouping"
            )
    
    # Recommendation 4: Next steps
    recommendations.append("→ Next: Analyze descriptions for semantic patterns")
    recommendations.append("→ Next: Cross-reference groups with PNT UDCs for validation")
    
    return recommendations


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def _trim_to_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce output to summary level only."""
    # Get full key attributes list
    key_attrs = results.get("key_attributes", [])
    
    # Build assumed facility groups from discovered patterns
    facility_groups = results.get("facility_groups", {})
    assumed_groups = []
    
    for group in facility_groups.get("groups", []):  # All groups - no limit
        assumed_groups.append({
            "group_id": group["group_id"],
            "facility_count": group["facility_count"],
            "percent_of_total": group["percent_of_total"],
            "key_attributes": group["key_filled_attributes"][:5],  # Top 5 attributes
            "attribute_count": group["attribute_count"],
            "facilities": group["facilities"],  # ALL facilities with id/desc/type
            "sample_facilities": group["sample_facilities"][:5]  # Show 5 samples
        })
    
    summary = {
        "total_facilities": results["total_facilities"],
        "total_columns": results["total_columns"],
        "analysis_timestamp": results["analysis_timestamp"],
        "key_attributes_count": len(key_attrs),
        "key_attributes": [
            {
                "column": attr["column"],
                "score": attr["score"],
                "fill_rate": attr["fill_rate"],
                "unique_count": attr["unique_count"],
                "category": attr["category"]
            }
            for attr in key_attrs  # Include ALL key attributes
        ],
        "top_5_attributes": [
            {
                "column": attr["column"],
                "score": attr["score"],
                "fill_rate": attr["fill_rate"]
            }
            for attr in key_attrs[:5]
        ],
        "facility_groups_found": facility_groups.get("total_groups", 0),
        "group_coverage_pct": facility_groups.get("coverage", 0),
        "assumed_facility_groups": assumed_groups,
        "recommendations": results.get("recommendations", [])
    }
    return summary


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def run_attribute_analysis(
    fac_filepath: str,
    fac_summary: Dict[str, Any],
    output_detail: str = "detailed"
) -> Dict[str, Any]:
    """
    Main entry point for attribute analysis.
    
    This is the function that should be called from main.py
    """
    return analyze_fac_attributes(fac_filepath, fac_summary, output_detail)
