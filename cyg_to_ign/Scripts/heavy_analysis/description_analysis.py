"""
Facility Description Analysis - Phase 2: Semantic Pattern Discovery

This module analyzes facility descriptions to:
1. Extract keywords from text fields (desc, type, category, info0, info1)
2. Validate Phase 1 attribute groupings with semantic analysis
3. Generate human-readable equipment type names
4. Build an equipment vocabulary for classification

This bridges the gap between attribute patterns (Phase 1) and UDC mapping (Phase 3).
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import re


# =============================================================================
# PHASE 2: DESCRIPTION ANALYSIS
# =============================================================================

def analyze_fac_descriptions(
    fac_filepath: str,
    fac_summary: Dict[str, Any],
    analysis_attributes: Dict[str, Any],
    output_detail: str = "summary"
) -> Dict[str, Any]:
    """
    Comprehensive description analysis of FAC dataset.
    
    Args:
        fac_filepath: Path to FAC CSV file
        fac_summary: Pre-computed summary from summaries.json
        analysis_attributes: Phase 1 results with assumed_facility_groups
        output_detail: Level of detail ("summary", "detailed", "full")
    
    Returns:
        {
            "equipment_vocabulary": {...},      # Master keyword vocabulary
            "assumed_equipment_types": [...],   # Named equipment types with confidence
            "group_validations": {...},         # Semantic coherence scores
            "keyword_extraction": {...},        # Raw keyword data
            "recommendations": [...]            # Next steps
        }
    """
    results = {
        "total_facilities": fac_summary.get("Total Rows", 0),
        "phase_1_groups": len(analysis_attributes.get("assumed_facility_groups", [])),
        "analysis_timestamp": pd.Timestamp.now().isoformat()
    }
    
    # Load FAC data
    fac_df = pd.read_csv(fac_filepath, encoding="utf-8", low_memory=False)
    
    # Extract assumed groups from Phase 1
    assumed_groups = analysis_attributes.get("assumed_facility_groups", [])
    
    # 1. Extract keywords for each group
    # Pass the entire analysis_attributes to access key_attributes at top level
    group_keywords = _extract_group_keywords(fac_df, assumed_groups, analysis_attributes)
    results["keyword_extraction"] = group_keywords
    
    # 2. Validate semantic coherence of each group
    validations = _validate_semantic_coherence(group_keywords)
    results["group_validations"] = validations
    
    # 3. Generate equipment type names and confidence scores
    equipment_types = _generate_equipment_types(fac_df, assumed_groups, group_keywords, validations)
    results["assumed_equipment_types"] = equipment_types
    
    # 4. Build master equipment vocabulary
    vocabulary = _build_equipment_vocabulary(equipment_types)
    results["equipment_vocabulary"] = vocabulary
    
    # 5. Generate recommendations
    recommendations = _generate_description_recommendations(results)
    results["recommendations"] = recommendations
    
    # Trim if summary mode
    if output_detail == "summary":
        results = _trim_description_summary(results)
    
    return results


# =============================================================================
# KEYWORD EXTRACTION
# =============================================================================

def _extract_group_keywords(
    fac_df: pd.DataFrame,
    assumed_groups: List[Dict[str, Any]],
    analysis_attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract keywords from ALL key attributes identified in Phase 1.
    
    This is critical because companies often misuse 'type' field.
    The real equipment info is in attr27, attr28, desc, id, etc.
    
    Uses simple word frequency analysis with:
    1. Compound word splitting
    2. Zero-variance detection (de-weight constants)
    3. Dynamic noise term filtering (auto-detect overly common terms)
    """
    # Get key attributes from top level of analysis_attributes (Phase 1 stores them there)
    key_attr_objs = analysis_attributes.get("key_attributes", [])
    if key_attr_objs and isinstance(key_attr_objs[0], dict):
        # Phase 1 stores key_attributes as list of objects: [{"column": "info0", ...}, ...]
        key_attr_names = [attr["column"] for attr in key_attr_objs]
    else:
        # Fallback to standard columns if key_attributes not provided
        key_attr_names = ['desc', 'type', 'category', 'info0', 'info1']
    
    # Always include desc and id for additional context
    analysis_columns = set(key_attr_names)
    analysis_columns.add('desc')
    analysis_columns.add('id')
    
    # Filter to columns that actually exist
    available_cols = [col for col in analysis_columns if col in fac_df.columns]
    
    # STEP 1: First pass - collect ALL keywords across all groups
    global_keyword_counts = Counter()
    total_facilities = len(fac_df)
    
    for group in assumed_groups:
        facilities = group.get("facilities", [])
        facility_ids = [f["id"] for f in facilities]
        group_facilities = fac_df[fac_df['id'].isin(facility_ids)]
        
        all_text = []
        for col in available_cols:
            text_values = group_facilities[col].dropna().astype(str)
            unique_vals = text_values.unique()
            
            if len(unique_vals) == 1:
                all_text.append(text_values.iloc[0])
            else:
                all_text.extend(text_values.tolist())
        
        keywords = _tokenize_and_count(all_text)
        global_keyword_counts.update(keywords)
    
    # STEP 2: Identify noise terms (appear in >75% of ALL facilities)
    # These are terms like "Towscada" that are too common to be discriminative
    noise_threshold = 0.75
    noise_terms = {
        word for word, count in global_keyword_counts.items()
        if count > (total_facilities * noise_threshold)
    }
    
    # STEP 3: Second pass - extract keywords per group, filtering noise
    group_keywords_data = []
    
    for group in assumed_groups:
        group_id = group["group_id"]
        facilities = group.get("facilities", [])
        facility_ids = [f["id"] for f in facilities]
        
        # Get facilities in this group
        group_facilities = fac_df[fac_df['id'].isin(facility_ids)]
        
        # Extract all text from descriptive columns
        # De-prioritize columns where ALL values are identical (zero variance)
        all_text = []
        for col in available_cols:
            text_values = group_facilities[col].dropna().astype(str)
            unique_vals = text_values.unique()
            
            if len(unique_vals) == 1:
                all_text.append(text_values.iloc[0])
            else:
                all_text.extend(text_values.tolist())
        
        # Tokenize and count keywords
        keywords = _tokenize_and_count(all_text)
        
        # Filter out noise terms dynamically detected
        filtered_keywords = Counter({
            word: count for word, count in keywords.items()
            if word not in noise_terms
        })
        
        # Get top keywords (after noise filtering)
        top_keywords = filtered_keywords.most_common(20)
        
        group_keywords_data.append({
            "group_id": group_id,
            "facility_count": len(facilities),
            "total_words": sum(keywords.values()),
            "unique_words": len(keywords),
            "filtered_unique_words": len(filtered_keywords),
            "top_keywords": [
                {"word": word, "count": count, "frequency": round(count / len(facilities), 2)}
                for word, count in top_keywords
            ]
        })
    
    return {
        "groups": group_keywords_data,
        "columns_analyzed": available_cols,
        "noise_terms_filtered": sorted(list(noise_terms)),
        "noise_threshold": noise_threshold
    }


def _tokenize_and_count(text_list: List[str]) -> Counter:
    """
    Tokenize text and count word frequencies.
    
    Enhanced implementation to handle company-specific patterns:
    - Split compound words: "WaterTank1" → ["water", "tank"]
    - Split underscores: "ARNETT_SWD_WT1" → ["arnett", "swd", "wt"]
    - Split camelCase: "productionWell" → ["production", "well"]
    - Remove universal stop words only (no company-specific hardcoding)
    """
    # Universal stop words to exclude (language-level only, no company terms)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'not', 'no', 'yes', 'n', 'na', 'nan', 'none'
    }
    
    word_counts = Counter()
    
    for text in text_list:
        if not text or pd.isna(text):
            continue
            
        text = str(text)
        
        # Step 1: Split by underscores and spaces first
        # "ARNETT_SWD_WT1" → ["ARNETT", "SWD", "WT1"]
        segments = re.split(r'[_\s\-]+', text)
        
        all_words = []
        for segment in segments:
            # Step 2: Split camelCase and extract compound words
            # "WaterTank1" → ["Water", "Tank", "1"]
            # Use regex to split on transitions: lowercase→uppercase, letter→number
            subsegments = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|[0-9]+', segment)
            all_words.extend(subsegments)
        
        # Step 3: Process and count words
        for word in all_words:
            word = word.lower().strip()
            
            # Skip if empty, stop word, single char, or pure number
            if not word:
                continue
            if word in stop_words:
                continue
            if len(word) <= 1:
                continue
            if word.isdigit():
                continue
            
            # Skip very short fragments (likely abbreviations without context)
            if len(word) == 2 and not word in ['wt', 'sd', 'hp', 'lp']:  # Allow some common abbrevs
                continue
            
            word_counts[word] += 1
    
    return word_counts


# =============================================================================
# SEMANTIC COHERENCE VALIDATION
# =============================================================================

def _validate_semantic_coherence(group_keywords: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that each group has coherent semantic patterns.
    
    High coherence = keywords are concentrated in a few dominant terms
    Low coherence = keywords are evenly distributed (no clear pattern)
    """
    validations = []
    
    for group_data in group_keywords.get("groups", []):
        top_keywords = group_data["top_keywords"]
        total_words = group_data["total_words"]
        unique_words = group_data["unique_words"]
        
        if len(top_keywords) == 0 or total_words == 0:
            validations.append({
                "group_id": group_data["group_id"],
                "coherence_score": 0.0,
                "confidence": "none",
                "reason": "No keywords found"
            })
            continue
        
        # Calculate coherence metrics
        # 1. Top keyword concentration (what % of words are in top 5?)
        top_5_count = sum(kw["count"] for kw in top_keywords[:5])
        concentration_ratio = top_5_count / total_words if total_words > 0 else 0
        
        # 2. Keyword diversity (unique words / total words)
        diversity_ratio = unique_words / total_words if total_words > 0 else 0
        
        # 3. Top keyword frequency (how often does #1 keyword appear per facility?)
        top_keyword_freq = top_keywords[0]["frequency"] if top_keywords else 0
        
        # Calculate coherence score (0-1)
        # High concentration + reasonable frequency = high coherence
        coherence_score = (concentration_ratio * 0.5) + (min(top_keyword_freq, 1.0) * 0.5)
        
        # Determine confidence level
        if coherence_score >= 0.7:
            confidence = "high"
        elif coherence_score >= 0.4:
            confidence = "medium"
        else:
            confidence = "low"
        
        validations.append({
            "group_id": group_data["group_id"],
            "coherence_score": round(coherence_score, 3),
            "confidence": confidence,
            "concentration_ratio": round(concentration_ratio, 3),
            "top_keyword_frequency": round(top_keyword_freq, 2),
            "unique_word_count": unique_words
        })
    
    return {
        "validations": validations,
        "high_confidence_groups": sum(1 for v in validations if v["confidence"] == "high"),
        "medium_confidence_groups": sum(1 for v in validations if v["confidence"] == "medium"),
        "low_confidence_groups": sum(1 for v in validations if v["confidence"] == "low")
    }


# =============================================================================
# EQUIPMENT TYPE GENERATION
# =============================================================================

def _generate_equipment_types(
    fac_df: pd.DataFrame,
    assumed_groups: List[Dict[str, Any]],
    group_keywords: Dict[str, Any],
    validations: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate named equipment types from groups + keywords + validation.
    
    NOTE: No consolidation at this stage - Phase 3 will consolidate based on UDC evidence.
    """
    equipment_types = []
    
    keyword_groups = {g["group_id"]: g for g in group_keywords.get("groups", [])}
    validation_map = {v["group_id"]: v for v in validations.get("validations", [])}
    
    for group in assumed_groups:
        group_id = group["group_id"]
        keywords_data = keyword_groups.get(group_id, {})
        validation_data = validation_map.get(group_id, {})
        
        # Get top keywords
        top_keywords = keywords_data.get("top_keywords", [])
        top_3_words = [kw["word"] for kw in top_keywords[:3]]
        
        # Generate suggested name from top keywords
        suggested_name = _generate_name_from_keywords(top_3_words)
        
        # Get ALL facilities from Phase 1
        facilities = group.get("facilities", [])
        facility_ids = [str(f["id"]) for f in facilities if "id" in f]
        
        # Get sample facilities for display
        sample_facilities = facilities[:3]
        
        equipment_types.append({
            "equipment_type_id": group_id,
            "suggested_name": suggested_name,
            "keywords": top_3_words,
            "facility_count": group["facility_count"],
            "percent_of_total": group["percent_of_total"],
            "facility_groups_matched": [group_id],
            "facility_ids": facility_ids,  # ALL facility IDs from Phase 1
            "key_attributes": group["key_attributes"],
            "confidence": validation_data.get("confidence", "unknown"),
            "coherence_score": validation_data.get("coherence_score", 0.0),
            "sample_facilities": sample_facilities,
            "sample_descriptions": [f["desc"] for f in sample_facilities if "desc" in f]
        })
    
    return equipment_types


def _generate_name_from_keywords(keywords: List[str]) -> str:
    """
    Generate a human-readable equipment type name from top keywords.
    """
    if not keywords:
        return "Unknown Equipment Type"
    
    # Special case handling for common terms
    keyword_str = " ".join(keywords).lower()
    
    # Wells
    if "well" in keyword_str:
        if "production" in keyword_str or "prod" in keyword_str:
            return "Production Wells"
        elif "injection" in keyword_str or "injector" in keyword_str:
            return "Injection Wells"
        elif "water" in keyword_str:
            return "Water Wells"
        else:
            return "Wells"
    
    # Meters
    if "meter" in keyword_str or "metering" in keyword_str:
        if "gas" in keyword_str:
            return "Gas Meters"
        elif "flow" in keyword_str:
            return "Flow Meters"
        else:
            return "Meters"
    
    # Separators
    if "separator" in keyword_str or "sep" in keyword_str:
        return "Separators"
    
    # Tanks
    if "tank" in keyword_str or "storage" in keyword_str:
        return "Tanks/Storage"
    
    # Compressors
    if "compressor" in keyword_str or "comp" in keyword_str:
        return "Compressors"
    
    # Pumps
    if "pump" in keyword_str:
        return "Pumps"
    
    # Heaters/Treaters
    if "heater" in keyword_str or "treater" in keyword_str:
        return "Heaters/Treaters"
    
    # Default: capitalize first keyword
    return keywords[0].title() + " Equipment"


# =============================================================================
# EQUIPMENT VOCABULARY
# =============================================================================

def _build_equipment_vocabulary(equipment_types: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build master vocabulary of equipment types and their keywords.
    """
    vocabulary = {}
    
    for eq_type in equipment_types:
        name = eq_type["suggested_name"]
        
        if name not in vocabulary:
            vocabulary[name] = {
                "keywords": set(),
                "facility_groups": [],
                "total_facilities": 0,
                "confidence_scores": []
            }
        
        vocabulary[name]["keywords"].update(eq_type["keywords"])
        vocabulary[name]["facility_groups"].extend(eq_type["facility_groups_matched"])
        vocabulary[name]["total_facilities"] += eq_type["facility_count"]
        vocabulary[name]["confidence_scores"].append(eq_type["coherence_score"])
    
    # Convert sets to lists and calculate averages
    vocab_output = {}
    for name, data in vocabulary.items():
        avg_confidence = sum(data["confidence_scores"]) / len(data["confidence_scores"]) if data["confidence_scores"] else 0
        
        vocab_output[name] = {
            "keywords": sorted(list(data["keywords"])),
            "facility_groups": data["facility_groups"],
            "total_facilities": data["total_facilities"],
            "average_confidence": round(avg_confidence, 3)
        }
    
    return vocab_output


# =============================================================================
# RECOMMENDATIONS
# =============================================================================

def _generate_description_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on Phase 2 analysis."""
    recommendations = []
    
    validations = results.get("group_validations", {})
    equipment_types = results.get("assumed_equipment_types", [])
    
    # High confidence groups
    high_conf = validations.get("high_confidence_groups", 0)
    if high_conf > 0:
        recommendations.append(f"✓ {high_conf} equipment types identified with high confidence")
    
    # Medium confidence
    med_conf = validations.get("medium_confidence_groups", 0)
    if med_conf > 0:
        recommendations.append(f"⚠ {med_conf} groups need review (medium confidence)")
    
    # Low confidence
    low_conf = validations.get("low_confidence_groups", 0)
    if low_conf > 0:
        recommendations.append(f"⚠ {low_conf} groups have low semantic coherence")
    
    # Equipment type diversity
    unique_names = len(set(eq["suggested_name"] for eq in equipment_types))
    recommendations.append(f"✓ Discovered {unique_names} distinct equipment type categories")
    
    # Next steps
    recommendations.append("→ Next: Run UDC bridge analysis to map equipment types to UDCs")
    recommendations.append("→ Next: Review low-confidence groups for refinement")
    
    return recommendations


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def _trim_description_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Trim output to summary level."""
    equipment_types = results.get("assumed_equipment_types", [])
    keyword_extraction = results.get("keyword_extraction", {})
    
    summary = {
        "total_facilities": results["total_facilities"],
        "phase_1_groups": results["phase_1_groups"],
        "analysis_timestamp": results["analysis_timestamp"],
        "equipment_types_discovered": len(set(eq["suggested_name"] for eq in equipment_types)),
        "assumed_equipment_types": [
            {
                "equipment_type_id": eq["equipment_type_id"],
                "suggested_name": eq["suggested_name"],
                "keywords": eq["keywords"],
                "facility_count": eq["facility_count"],
                "percent_of_total": eq["percent_of_total"],
                "facility_ids": eq["facility_ids"],  # Keep facility_ids for Phase 3
                "confidence": eq["confidence"],
                "coherence_score": eq["coherence_score"]
            }
            for eq in equipment_types
        ],
        "equipment_vocabulary": results.get("equipment_vocabulary", {}),
        "validation_summary": {
            "high_confidence": results.get("group_validations", {}).get("high_confidence_groups", 0),
            "medium_confidence": results.get("group_validations", {}).get("medium_confidence_groups", 0),
            "low_confidence": results.get("group_validations", {}).get("low_confidence_groups", 0)
        },
        "noise_filtering": {
            "noise_terms_filtered": keyword_extraction.get("noise_terms_filtered", []),
            "noise_threshold": keyword_extraction.get("noise_threshold", 0.75),
            "columns_analyzed": keyword_extraction.get("columns_analyzed", [])
        },
        "recommendations": results.get("recommendations", [])
    }
    
    return summary


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def run_description_analysis(
    fac_filepath: str,
    fac_summary: Dict[str, Any],
    analysis_attributes: Dict[str, Any],
    output_detail: str = "summary"
) -> Dict[str, Any]:
    """
    Main entry point for description analysis (Phase 2).
    
    This should be called from main.py after Phase 1 completes.
    """
    return analyze_fac_descriptions(fac_filepath, fac_summary, analysis_attributes, output_detail)
