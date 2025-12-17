"""
Facility UDC Bridge Analysis - Phase 3: UDC Validation & Hierarchy Building

This module validates equipment types using technical UDC evidence from PNT tags:
1. UDC-Based Validation - Calculate UDC coverage per equipment type
2. Equipment Hierarchy Discovery - Build parent-child relationships via Jaccard similarity
3. Group Consolidation - Merge groups with >80% UDC overlap
4. Confidence Analysis - Deep dive validation of high/medium/low confidence groups

This bridges Phase 2 (semantic patterns) with Phase 4 (function inference) using
hard technical evidence from the actual tag configurations.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from pathlib import Path
import os


# =============================================================================
# PHASE 3: UDC BRIDGE ANALYSIS
# =============================================================================

def analyze_udc_bridge(
    merged_dataset_path: str,
    analysis_descriptions: Dict[str, Any],
    output_detail: str = "summary"
) -> Dict[str, Any]:
    """
    Comprehensive UDC-based validation and hierarchy discovery.
    
    Args:
        merged_dataset_path: Path to merged_validation_dataset.csv
        analysis_descriptions: Phase 2 results with assumed_equipment_types (includes facility_ids)
        output_detail: Level of detail ("summary", "detailed", "full")
    
    Returns:
        {
            "equipment_udc_profiles": [...],    # UDC coverage per equipment type
            "equipment_hierarchy": {...},       # Parent-child relationships
            "consolidated_groups": [...],       # Merged equipment types
            "confidence_analysis": {...},       # Validation of high/medium/low
            "hierarchy_tree_path": "...",       # Path to saved ASCII tree
            "recommendations": [...]            # Next steps
        }
    """
    results = {
        "total_equipment_types": len(analysis_descriptions.get("assumed_equipment_types", [])),
        "analysis_timestamp": pd.Timestamp.now().isoformat()
    }
    
    # Load merged dataset
    if not os.path.exists(merged_dataset_path):
        return {
            "error": f"Merged dataset not found: {merged_dataset_path}",
            "recommendation": "Run create-merged-validation-dataset first"
        }
    
    try:
        merged_df = pd.read_csv(merged_dataset_path, low_memory=False)
        results["total_tags_analyzed"] = len(merged_df)
    except Exception as e:
        return {"error": f"Failed to load merged dataset: {e}"}
    
    # Get equipment types from Phase 2 (already includes facility_ids)
    equipment_types = analysis_descriptions.get("assumed_equipment_types", [])
    if not equipment_types:
        return {
            "error": "No equipment types found in analysis_descriptions",
            "recommendation": "Run analyze-descriptions first"
        }
    
    # Step 1: UDC-Based Validation
    udc_profiles = _validate_equipment_with_udcs(
        merged_df=merged_df,
        equipment_types=equipment_types,
        output_detail=output_detail
    )
    results["equipment_udc_profiles"] = udc_profiles
    
    # Step 2: Equipment Hierarchy Discovery
    hierarchy = _build_hierarchy_tree(
        udc_profiles=udc_profiles,
        equipment_types=equipment_types,
        output_detail=output_detail
    )
    results["equipment_hierarchy"] = hierarchy
    
    # Step 3: Group Consolidation
    consolidated = _consolidate_groups(
        udc_profiles=udc_profiles,
        equipment_types=equipment_types,
        merge_threshold=0.80
    )
    results["consolidated_groups"] = consolidated
    
    # Step 4: Confidence Level Deep Dives
    confidence_analysis = _analyze_confidence_levels(
        udc_profiles=udc_profiles,
        equipment_types=equipment_types,
        consolidated=consolidated
    )
    results["confidence_analysis"] = confidence_analysis
    
    # Generate ASCII tree and save to analytical_output
    tree_path = _generate_hierarchy_txt(
        hierarchy=hierarchy,
        udc_profiles=udc_profiles,
        equipment_types=equipment_types
    )
    results["hierarchy_tree_path"] = tree_path
    
    # Generate recommendations
    results["recommendations"] = _generate_udc_recommendations(results)
    
    # Trim to summary if requested
    if output_detail == "summary":
        results = _trim_udc_summary(results)
    
    return results


# =============================================================================
# FACILITY ID ENRICHMENT
# =============================================================================

def _enrich_with_facility_ids(
    equipment_types: List[Dict[str, Any]],
    phase1_groups: List[Dict[str, Any]],
    fac_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Enrich Phase 2 equipment types with ALL facility IDs from Phase 1 groups.
    
    Strategy: Use Phase 1's facility_indices to get facility IDs from FAC dataset.
    This gives us the complete list of facilities for each equipment type.
    """
    enriched_types = []
    
    # Build lookup from group_id to facility IDs
    group_facility_map = {}
    for group in phase1_groups:
        group_id = group.get("group_id")
        facility_indices = group.get("facility_indices", [])
        
        # Convert indices to facility IDs
        facility_ids = []
        for idx in facility_indices:
            if idx < len(fac_df):
                facility_id = fac_df.iloc[idx].get("id")
                if pd.notna(facility_id):
                    facility_ids.append(str(facility_id))
        
        group_facility_map[group_id] = facility_ids
    
    # Enrich each equipment type
    for eq_type in equipment_types:
        eq_copy = eq_type.copy()
        
        # Get all Phase 1 groups this equipment type matches
        matched_groups = eq_type.get("facility_groups_matched", [])
        
        # Collect all facility IDs from matched groups
        all_facility_ids = []
        for group_id in matched_groups:
            all_facility_ids.extend(group_facility_map.get(group_id, []))
        
        # Update facility_ids with complete list
        eq_copy["facility_ids"] = all_facility_ids
        
        enriched_types.append(eq_copy)
    
    return enriched_types


# =============================================================================
# STEP 1: UDC-BASED VALIDATION
# =============================================================================

def _validate_equipment_with_udcs(
    merged_df: pd.DataFrame,
    equipment_types: List[Dict[str, Any]],
    output_detail: str
) -> List[Dict[str, Any]]:
    """
    For each equipment type, calculate UDC coverage and classify UDCs.
    
    Returns:
        [
            {
                "equipment_type_id": 1,
                "suggested_name": "Gas Meters",
                "facility_count": 698,
                "facility_ids": [12, 45, 67, ...],
                "total_tags": 5234,
                "distinct_udcs": 12,
                "udc_coverage": {
                    "FLOWGAS": {"count": 698, "coverage_pct": 100.0, "class": "core"},
                    "PRESSLINE": {"count": 690, "coverage_pct": 98.9, "class": "core"},
                    "COMPRATIO": {"count": 345, "coverage_pct": 49.4, "class": "optional"}
                }
            }
        ]
    """
    profiles = []
    
    for eq_type in equipment_types:
        eq_id = eq_type.get("equipment_type_id")
        eq_name = eq_type.get("suggested_name")  # Phase 2 uses 'suggested_name'
        facility_ids = eq_type.get("facility_ids", [])
        
        if not facility_ids:
            continue
        
        # Filter merged dataset to this equipment type's facilities
        eq_tags = merged_df[merged_df["fac_id"].isin(facility_ids)].copy()
        
        if len(eq_tags) == 0:
            profiles.append({
                "equipment_type_id": eq_id,
                "suggested_name": eq_name,
                "facility_count": len(facility_ids),
                "facility_ids": facility_ids if output_detail == "full" else facility_ids[:10],
                "total_tags": 0,
                "distinct_udcs": 0,
                "udc_coverage": {},
                "warning": "No PNT tags found for these facilities"
            })
            continue
        
        # Calculate UDC coverage
        total_facilities = len(facility_ids)
        udc_stats = defaultdict(lambda: {"facilities": set(), "tag_count": 0})
        
        for _, row in eq_tags.iterrows():
            udc = row.get("pnt_uniformdatacode")  # Merged dataset uses pnt_ prefix
            fac_id = row.get("fac_id")
            if pd.notna(udc) and pd.notna(fac_id):
                udc_stats[udc]["facilities"].add(fac_id)
                udc_stats[udc]["tag_count"] += 1
        
        # Build UDC coverage dict with classification
        udc_coverage = {}
        for udc, stats in udc_stats.items():
            coverage_pct = (len(stats["facilities"]) / total_facilities) * 100
            
            # Classify UDC
            if coverage_pct >= 80:
                udc_class = "core"
            elif coverage_pct >= 50:
                udc_class = "common"
            else:
                udc_class = "optional"
            
            udc_coverage[udc] = {
                "count": len(stats["facilities"]),
                "tag_count": stats["tag_count"],
                "coverage_pct": round(coverage_pct, 2),
                "class": udc_class
            }
        
        # Sort UDCs by coverage (descending)
        udc_coverage = dict(sorted(
            udc_coverage.items(),
            key=lambda x: x[1]["coverage_pct"],
            reverse=True
        ))
        
        profiles.append({
            "equipment_type_id": eq_id,
            "suggested_name": eq_name,
            "facility_count": total_facilities,
            "facility_ids": facility_ids if output_detail == "full" else facility_ids[:10],
            "total_tags": len(eq_tags),
            "distinct_udcs": len(udc_coverage),
            "udc_coverage": udc_coverage
        })
    
    return profiles


# =============================================================================
# STEP 2: EQUIPMENT HIERARCHY DISCOVERY
# =============================================================================

def _build_hierarchy_tree(
    udc_profiles: List[Dict[str, Any]],
    equipment_types: List[Dict[str, Any]],
    output_detail: str
) -> Dict[str, Any]:
    """
    Build parent-child relationships using Jaccard similarity on UDC sets.
    
    Returns:
        {
            "similarity_matrix": {...},
            "parent_child_relationships": [
                {"parent_id": 1, "child_id": 5, "similarity": 0.87, "shared_udcs": [...]}
            ],
            "root_nodes": [1, 3, 7],  # Equipment types with no parents
            "isolated_nodes": [12]     # Equipment types with no relationships
        }
    """
    # Extract core UDC sets for each equipment type
    eq_udc_sets = {}
    for profile in udc_profiles:
        eq_id = profile["equipment_type_id"]
        # Only use core and common UDCs for hierarchy (>= 50% coverage)
        core_udcs = {
            udc for udc, stats in profile.get("udc_coverage", {}).items()
            if stats["class"] in ["core", "common"]
        }
        eq_udc_sets[eq_id] = core_udcs
    
    # Build similarity matrix
    similarity_matrix = {}
    relationships = []
    
    eq_ids = list(eq_udc_sets.keys())
    for i, eq_a in enumerate(eq_ids):
        similarity_matrix[eq_a] = {}
        for eq_b in eq_ids:
            if eq_a == eq_b:
                similarity_matrix[eq_a][eq_b] = 1.0
                continue
            
            # Calculate Jaccard similarity
            jaccard = _calculate_jaccard_similarity(
                eq_udc_sets[eq_a],
                eq_udc_sets[eq_b]
            )
            similarity_matrix[eq_a][eq_b] = jaccard
            
            # If similarity > 60%, consider hierarchy relationship
            if jaccard > 0.60 and eq_a != eq_b:
                # Determine parent/child (larger group = parent)
                profile_a = next(p for p in udc_profiles if p["equipment_type_id"] == eq_a)
                profile_b = next(p for p in udc_profiles if p["equipment_type_id"] == eq_b)
                
                if profile_a["facility_count"] > profile_b["facility_count"]:
                    parent_id, child_id = eq_a, eq_b
                else:
                    parent_id, child_id = eq_b, eq_a
                
                # Calculate shared UDCs
                shared_udcs = list(eq_udc_sets[eq_a] & eq_udc_sets[eq_b])
                
                relationships.append({
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "similarity": round(jaccard, 3),
                    "shared_udcs": shared_udcs,
                    "shared_udc_count": len(shared_udcs)
                })
    
    # Find root nodes (no parents) and isolated nodes (no relationships)
    all_children = {r["child_id"] for r in relationships}
    all_connected = {r["parent_id"] for r in relationships} | all_children
    
    root_nodes = [eq_id for eq_id in eq_ids if eq_id not in all_children and eq_id in all_connected]
    isolated_nodes = [eq_id for eq_id in eq_ids if eq_id not in all_connected]
    
    return {
        "similarity_matrix": similarity_matrix if output_detail == "full" else {},
        "parent_child_relationships": relationships,
        "root_nodes": root_nodes,
        "isolated_nodes": isolated_nodes,
        "total_relationships": len(relationships)
    }


def _calculate_jaccard_similarity(set_a: Set, set_b: Set) -> float:
    """
    Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
    """
    if not set_a and not set_b:
        return 0.0
    
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    
    if union == 0:
        return 0.0
    
    return intersection / union


# =============================================================================
# STEP 3: GROUP CONSOLIDATION
# =============================================================================

def _consolidate_groups(
    udc_profiles: List[Dict[str, Any]],
    equipment_types: List[Dict[str, Any]],
    merge_threshold: float = 0.80
) -> Dict[str, Any]:
    """
    Merge equipment types with >80% UDC overlap.
    
    Returns:
        {
            "merged_groups": [
                {
                    "new_group_id": 1,
                    "new_group_name": "Combined Gas/Flow Meters",
                    "merged_from": [2, 5],
                    "total_facilities": 1234,
                    "merge_reason": "UDC overlap: 87%"
                }
            ],
            "unchanged_groups": [1, 3, 7, ...],
            "consolidation_summary": {
                "before": 14,
                "after": 12,
                "merged": 2
            }
        }
    """
    merged_groups = []
    merged_ids = set()
    
    # Build UDC sets for comparison
    eq_udc_sets = {}
    for profile in udc_profiles:
        eq_id = profile["equipment_type_id"]
        all_udcs = set(profile.get("udc_coverage", {}).keys())
        eq_udc_sets[eq_id] = all_udcs
    
    # Find merge candidates
    eq_ids = list(eq_udc_sets.keys())
    for i, eq_a in enumerate(eq_ids):
        if eq_a in merged_ids:
            continue
        
        for eq_b in eq_ids[i+1:]:
            if eq_b in merged_ids:
                continue
            
            # Calculate overlap
            jaccard = _calculate_jaccard_similarity(
                eq_udc_sets[eq_a],
                eq_udc_sets[eq_b]
            )
            
            if jaccard >= merge_threshold:
                # Merge these groups
                profile_a = next(p for p in udc_profiles if p["equipment_type_id"] == eq_a)
                profile_b = next(p for p in udc_profiles if p["equipment_type_id"] == eq_b)
                
                type_a = next(t for t in equipment_types if t["equipment_type_id"] == eq_a)
                type_b = next(t for t in equipment_types if t["equipment_type_id"] == eq_b)
                
                merged_groups.append({
                    "new_group_id": eq_a,  # Keep first group's ID
                    "new_group_name": f"{type_a['suggested_name']} + {type_b['suggested_name']}",
                    "merged_from": [eq_a, eq_b],
                    "total_facilities": profile_a["facility_count"] + profile_b["facility_count"],
                    "merge_reason": f"UDC overlap: {jaccard*100:.1f}%",
                    "combined_udcs": len(eq_udc_sets[eq_a] | eq_udc_sets[eq_b])
                })
                
                merged_ids.add(eq_a)
                merged_ids.add(eq_b)
                break  # Only merge once per group
    
    unchanged_groups = [eq_id for eq_id in eq_ids if eq_id not in merged_ids]
    
    return {
        "merged_groups": merged_groups,
        "unchanged_groups": unchanged_groups,
        "consolidation_summary": {
            "before": len(equipment_types),
            "after": len(unchanged_groups) + len(merged_groups),
            "merged": len(merged_ids)
        }
    }


# =============================================================================
# STEP 4: CONFIDENCE LEVEL ANALYSIS
# =============================================================================

def _analyze_confidence_levels(
    udc_profiles: List[Dict[str, Any]],
    equipment_types: List[Dict[str, Any]],
    consolidated: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deep dive into high/medium/low confidence groups.
    
    Returns:
        {
            "high_confidence": {
                "count": 42,
                "validated": 40,
                "avg_udc_count": 8.5,
                "avg_core_udc_coverage": 92.3
            },
            "medium_confidence": {...},
            "low_confidence": {...},
            "recommendations_by_level": {...}
        }
    """
    # Group profiles by confidence level
    confidence_groups = {
        "high": [],
        "medium": [],
        "low": []
    }
    
    for profile in udc_profiles:
        eq_id = profile["equipment_type_id"]
        eq_type = next((t for t in equipment_types if t["equipment_type_id"] == eq_id), None)
        if not eq_type:
            continue
        
        confidence = eq_type.get("confidence_level", "unknown")
        if confidence in confidence_groups:
            confidence_groups[confidence].append(profile)
    
    # Analyze each confidence level
    analysis = {}
    for level, profiles in confidence_groups.items():
        if not profiles:
            analysis[f"{level}_confidence"] = {"count": 0}
            continue
        
        # Calculate metrics
        udc_counts = [p["distinct_udcs"] for p in profiles]
        
        # Calculate average core UDC coverage
        core_coverages = []
        for p in profiles:
            core_udcs = [
                stats["coverage_pct"] 
                for udc, stats in p.get("udc_coverage", {}).items() 
                if stats["class"] == "core"
            ]
            if core_udcs:
                core_coverages.append(np.mean(core_udcs))
        
        analysis[f"{level}_confidence"] = {
            "count": len(profiles),
            "avg_udc_count": round(np.mean(udc_counts), 2) if udc_counts else 0,
            "min_udc_count": min(udc_counts) if udc_counts else 0,
            "max_udc_count": max(udc_counts) if udc_counts else 0,
            "avg_core_udc_coverage": round(np.mean(core_coverages), 2) if core_coverages else 0,
            "equipment_types": [
                {
                    "id": p["equipment_type_id"],
                    "name": next(t["suggested_name"] for t in equipment_types if t["equipment_type_id"] == p["equipment_type_id"]),
                    "distinct_udcs": p["distinct_udcs"],
                    "facilities": p["facility_count"]
                }
                for p in profiles[:5]  # Show top 5
            ]
        }
    
    # Generate recommendations by confidence level
    recommendations = {
        "high_confidence": "✓ Ready for Ignition UDT generation - UDC profiles validated",
        "medium_confidence": "⚠ Review UDC patterns - may need manual refinement",
        "low_confidence": "🔍 Deep analysis required - consider splitting in Phase 4"
    }
    
    analysis["recommendations_by_level"] = recommendations
    
    return analysis


# =============================================================================
# ASCII TREE GENERATION
# =============================================================================

def _generate_hierarchy_txt(
    hierarchy: Dict[str, Any],
    udc_profiles: List[Dict[str, Any]],
    equipment_types: List[Dict[str, Any]]
) -> str:
    """
    Generate ASCII tree visualization and save to analytical_output folder.
    
    Returns: Path to saved file
    """
    # Determine output path
    from cyg_to_ign.Scripts import common
    root_folder = common.getRootFolder()
    output_dir = os.path.join(root_folder, "analytical_output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "equipment_hierarchy.txt")
    
    lines = []
    lines.append("=" * 80)
    lines.append("FACILITY EQUIPMENT HIERARCHY")
    lines.append("=" * 80)
    lines.append(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Equipment Types: {len(equipment_types)}")
    lines.append(f"Hierarchical Relationships: {hierarchy['total_relationships']}")
    lines.append("=" * 80)
    lines.append("")
    
    # Build tree structure
    relationships = hierarchy.get("parent_child_relationships", [])
    root_nodes = hierarchy.get("root_nodes", [])
    isolated_nodes = hierarchy.get("isolated_nodes", [])
    
    # Helper to format a node
    def format_node(eq_id: int, indent: int = 0, is_last: bool = False, prefix: str = ""):
        eq_type = next((t for t in equipment_types if t["equipment_type_id"] == eq_id), None)
        profile = next((p for p in udc_profiles if p["equipment_type_id"] == eq_id), None)
        
        if not eq_type or not profile:
            return []
        
        # Node info
        name = eq_type["suggested_name"]
        facilities = profile["facility_count"]
        confidence = eq_type.get("confidence", "unknown").upper()
        conf_score = eq_type.get("coherence_score", 0)
        keywords = eq_type.get("keywords", [])
        
        # UDC statistics
        udc_coverage = profile.get("udc_coverage", {})
        total_tags = profile.get("total_tags", 0)
        distinct_udcs = profile.get("distinct_udcs", 0)
        
        # Classify UDCs
        core_udcs = [(udc, stats) for udc, stats in udc_coverage.items() if stats["class"] == "core"]
        common_udcs = [(udc, stats) for udc, stats in udc_coverage.items() if stats["class"] == "common"]
        
        # Sample facilities
        sample_facilities = profile.get("facility_ids", [])[:3]
        
        # Build main line
        connector = "└── " if is_last else "├── "
        line = f"{prefix}{connector}[{confidence}] {name} ({facilities} facilities, {total_tags} tags)"
        node_lines = [line]
        
        child_prefix = prefix + ("    " if is_last else "│   ")
        
        # Add keywords
        if keywords:
            node_lines.append(f"{child_prefix}Keywords: {', '.join(keywords)}")
        
        # Add UDC statistics
        if distinct_udcs > 0:
            node_lines.append(f"{child_prefix}UDCs: {distinct_udcs} distinct ({len(core_udcs)} core, {len(common_udcs)} common)")
            
            # Show top 5 core UDCs with coverage
            if core_udcs:
                node_lines.append(f"{child_prefix}Core UDCs:")
                for udc, stats in sorted(core_udcs, key=lambda x: x[1]["coverage_pct"], reverse=True)[:5]:
                    node_lines.append(f"{child_prefix}  • {udc}: {stats['coverage_pct']:.1f}% coverage ({stats['count']} facilities)")
                if len(core_udcs) > 5:
                    node_lines.append(f"{child_prefix}  ... and {len(core_udcs) - 5} more core UDCs")
        else:
            node_lines.append(f"{child_prefix}⚠ No UDCs found for this equipment type")
        
        # Add sample facilities
        if sample_facilities:
            node_lines.append(f"{child_prefix}Sample Facilities: {', '.join(sample_facilities[:3])}")
        
        return node_lines
    
    # Process root nodes and their children
    if root_nodes:
        lines.append("ROOT EQUIPMENT CATEGORIES")
        lines.append("-" * 80)
        lines.append("")
        
        for i, root_id in enumerate(root_nodes):
            is_last_root = (i == len(root_nodes) - 1)
            
            # Add root node
            lines.extend(format_node(root_id, indent=0, is_last=is_last_root))
            
            # Find children of this root
            children = [r for r in relationships if r["parent_id"] == root_id]
            for j, child_rel in enumerate(children):
                is_last_child = (j == len(children) - 1)
                prefix = "    " if is_last_root else "│   "
                lines.extend(format_node(child_rel["child_id"], indent=1, is_last=is_last_child, prefix=prefix))
            
            if not is_last_root:
                lines.append("│")
        
        lines.append("")
    
    # Process isolated nodes
    if isolated_nodes:
        lines.append("=" * 80)
        lines.append("ISOLATED EQUIPMENT TYPES (No Hierarchical Relationships)")
        lines.append("-" * 80)
        lines.append("")
        
        for i, iso_id in enumerate(isolated_nodes):
            is_last = (i == len(isolated_nodes) - 1)
            lines.extend(format_node(iso_id, indent=0, is_last=is_last))
        
        lines.append("")
    
    # Add summary statistics
    lines.append("=" * 80)
    lines.append("SUMMARY STATISTICS")
    lines.append("-" * 80)
    lines.append(f"Root Categories: {len(root_nodes)}")
    lines.append(f"Hierarchical Children: {len(set(r['child_id'] for r in relationships))}")
    lines.append(f"Isolated Types: {len(isolated_nodes)}")
    lines.append(f"Average Jaccard Similarity: {np.mean([r['similarity'] for r in relationships]):.3f}" if relationships else "N/A")
    lines.append("=" * 80)
    
    # Write to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return output_path
    except Exception as e:
        return f"ERROR: Failed to write hierarchy tree: {e}"


# =============================================================================
# RECOMMENDATIONS
# =============================================================================

def _generate_udc_recommendations(results: Dict[str, Any]) -> List[str]:
    """
    Generate actionable recommendations based on UDC analysis results.
    """
    recommendations = []
    
    # Check hierarchy
    hierarchy = results.get("equipment_hierarchy", {})
    if hierarchy.get("total_relationships", 0) > 0:
        recommendations.append(
            f"✓ Discovered {hierarchy['total_relationships']} hierarchical relationships - review tree"
        )
    
    # Check consolidation
    consolidated = results.get("consolidated_groups", {})
    if consolidated.get("consolidation_summary", {}).get("merged", 0) > 0:
        merged_count = consolidated["consolidation_summary"]["merged"]
        recommendations.append(
            f"⚠ {merged_count} groups mergeable (>80% UDC overlap) - consider consolidation"
        )
    
    # Check confidence analysis
    confidence = results.get("confidence_analysis", {})
    low_conf = confidence.get("low_confidence", {}).get("count", 0)
    if low_conf > 0:
        recommendations.append(
            f"🔍 {low_conf} low-confidence groups need deeper analysis in Phase 4"
        )
    
    # Next steps
    recommendations.append("→ Review equipment_hierarchy.txt for visual structure")
    recommendations.append("→ Next: Phase 4 - Equipment function inference")
    
    return recommendations


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def _trim_udc_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trim results to summary-level detail for summaries.json.
    """
    summary = {
        "total_equipment_types": results.get("total_equipment_types"),
        "total_tags_analyzed": results.get("total_tags_analyzed"),
        "analysis_timestamp": results.get("analysis_timestamp"),
        "hierarchy_tree_path": results.get("hierarchy_tree_path"),
    }
    
    # Summarize UDC profiles
    profiles = results.get("equipment_udc_profiles", [])
    summary["udc_profile_summary"] = {
        "total_profiles": len(profiles),
        "avg_udcs_per_type": round(np.mean([p["distinct_udcs"] for p in profiles]), 2) if profiles else 0,
        "total_distinct_udcs": len(set(
            udc 
            for p in profiles 
            for udc in p.get("udc_coverage", {}).keys()
        ))
    }
    
    # Include top 5 profiles (by facility count)
    top_profiles = sorted(profiles, key=lambda p: p["facility_count"], reverse=True)[:5]
    summary["top_equipment_types"] = [
        {
            "id": p["equipment_type_id"],
            "name": p["suggested_name"],
            "facilities": p["facility_count"],
            "distinct_udcs": p["distinct_udcs"],
            "core_udcs": [
                udc for udc, stats in p.get("udc_coverage", {}).items()
                if stats["class"] == "core"
            ]
        }
        for p in top_profiles
    ]
    
    # Hierarchy summary
    hierarchy = results.get("equipment_hierarchy", {})
    summary["hierarchy_summary"] = {
        "total_relationships": hierarchy.get("total_relationships", 0),
        "root_nodes_count": len(hierarchy.get("root_nodes", [])),
        "isolated_nodes_count": len(hierarchy.get("isolated_nodes", []))
    }
    
    # Consolidation summary
    consolidated = results.get("consolidated_groups", {})
    summary["consolidation_summary"] = consolidated.get("consolidation_summary", {})
    
    # Confidence analysis
    confidence = results.get("confidence_analysis", {})
    summary["confidence_summary"] = {
        "high_confidence_count": confidence.get("high_confidence", {}).get("count", 0),
        "medium_confidence_count": confidence.get("medium_confidence", {}).get("count", 0),
        "low_confidence_count": confidence.get("low_confidence", {}).get("count", 0)
    }
    
    # Recommendations
    summary["recommendations"] = results.get("recommendations", [])
    
    return summary


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def run_udc_bridge_analysis(
    merged_dataset_path: str,
    analysis_descriptions: Dict[str, Any],
    output_detail: str = "summary"
) -> Dict[str, Any]:
    """
    Main entry point for Phase 3 UDC Bridge Analysis.
    
    This function orchestrates all Phase 3 operations:
    1. Validates equipment types with UDC evidence (queries merged dataset using facility_ids)
    2. Builds equipment hierarchy via Jaccard similarity on UDC sets
    3. Consolidates overlapping groups (>80% UDC overlap)
    4. Analyzes confidence levels with UDC metrics
    5. Generates ASCII tree visualization
    
    Args:
        merged_dataset_path: Path to merged_validation_dataset.csv (TRS+PNT+FAC joined dataset)
        analysis_descriptions: Phase 2 results (equipment types with facility_ids pre-populated)
        output_detail: "summary", "detailed", or "full"
    
    Returns:
        Complete Phase 3 analysis results with UDC profiles, hierarchy, and consolidation
    
    Note:
        Equipment types from Phase 2 already have facility_ids populated from Phase 1 facilities list.
        No FAC file or Phase 1 data needed - we query merged_validation_dataset.csv directly.
    """
    return analyze_udc_bridge(
        merged_dataset_path=merged_dataset_path,
        analysis_descriptions=analysis_descriptions,
        output_detail=output_detail
    )
