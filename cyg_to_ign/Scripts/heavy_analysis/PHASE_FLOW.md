# Phase 1 → Phase 2: How Results Flow Into Description Analysis
---

## How Phase 2 Uses Phase 1 Results

### Phase 2: `description_analysis.py` (Semantic Pattern Discovery)

**Goal**: Extract meaning from text fields to:
1. Validate/refine the facility groups from Phase 1
2. Generate human-readable names for each group
3. Discover equipment type keywords
4. Build a vocabulary for future classification

---

## Phase 2 Strategy: Multi-Step Description Analysis

### Step 1: Load Phase 1 Results
```python
# Load the key attributes and assumed groups
analysis_attrs = summaries["analysis_attributes"]
key_attrs = analysis_attrs["key_attributes"]
assumed_groups = analysis_attrs["assumed_facility_groups"]
```

### Step 2: Keyword Extraction from Descriptive Columns

**For each key descriptive attribute** (type, desc, category, info0, info1):

1. **Tokenize & Clean**
   - Extract words from text fields
   - Remove stop words, numbers, special chars
   - Normalize (lowercase, stem/lemmatize)

2. **Build TF-IDF Matrix**
   - Calculate term frequency - inverse document frequency
   - Identifies words that are distinctive to specific facilities
   - Example: "METER" appears in 15% of facilities → high IDF score

3. **Extract Top Keywords Per Group**
   - For each `assumed_facility_group`, analyze descriptions
   - Find words that appear frequently WITHIN group but rarely OUTSIDE
   - Example Group 1 keywords: ["well", "production", "oil", "gas"]
   - Example Group 2 keywords: ["meter", "measurement", "flow"]

### Step 3: Semantic Clustering Validation

**Cross-validate attribute patterns with semantic patterns**:

```python
# Pseudo-code for validation
for group in assumed_groups:
    # Get facilities in this group (by attribute signature)
    facilities = get_facilities_by_signature(group)
    
    # Extract descriptions
    descriptions = facilities[["desc", "type", "info0", "info1"]]
    
    # Analyze keywords
    keywords = extract_keywords(descriptions)
    
    # Does semantic clustering match attribute clustering?
    semantic_coherence_score = calculate_coherence(keywords)
    
    if semantic_coherence_score > 0.7:
        # Strong match - this is likely a real equipment type
        group["confidence"] = "high"
        group["suggested_name"] = generate_name_from_keywords(keywords)
    else:
        # Weak match - might need further refinement
        group["confidence"] = "needs_review"
```

### Step 4: Equipment Type Vocabulary Building

**Create a master vocabulary**:

```python
equipment_vocabulary = {
    "wells": {
        "keywords": ["well", "production", "oil", "gas", "producer", "injector"],
        "attribute_signature": ["type", "attr2", "attr7", "attr27"],
        "facility_groups": [1, 5],  # Group IDs that match
        "confidence": 0.89
    },
    "meters": {
        "keywords": ["meter", "measurement", "flow", "totalizer", "orifice"],
        "attribute_signature": ["type", "attr3", "attr12", "attr25"],
        "facility_groups": [2],
        "confidence": 0.92
    },
    "separators": {
        "keywords": ["separator", "sep", "treater", "heater"],
        "attribute_signature": ["type", "category", "attr2", "attr13"],
        "facility_groups": [3, 7],
        "confidence": 0.78
    }
}
```

### Step 5: Generate "Assumed Equipment Types"

**Output a refined mapping**:

```json
{
  "analysis_descriptions": {
    "vocabulary_size": 247,
    "equipment_types_discovered": 8,
    "assumed_equipment_types": [
      {
        "equipment_type_id": 1,
        "suggested_name": "Production Wells",
        "keywords": ["well", "production", "oil", "gas"],
        "facility_count": 1847,
        "facility_groups_matched": [1],
        "key_attributes": ["type", "category", "attr2", "attr7"],
        "confidence": "high",
        "sample_descriptions": [
          "WELL - OIL PRODUCER - ZONE A",
          "PRODUCTION WELL - GAS LIFT",
          "WELL - WATER INJECTION"
        ]
      },
      {
        "equipment_type_id": 2,
        "suggested_name": "Flow Meters",
        "keywords": ["meter", "flow", "measurement"],
        "facility_count": 943,
        "facility_groups_matched": [2],
        "key_attributes": ["type", "info1", "attr3", "attr12"],
        "confidence": "high",
        "sample_descriptions": [
          "ORIFICE METER - GAS",
          "TURBINE METER - LIQUID",
          "CORIOLIS METER - CUSTODY"
        ]
      }
    ]
  }
}
```

---

## Phase 3 Implementation

### Usage

```bash
>>> analyze-udcs
```

**Prerequisites**:
1. Phase 1 completed (`analyze-attributes`)
2. Phase 2 completed (`analyze-descriptions`)
3. Merged validation dataset created (`validate-all`)

**What it does**:
1. Loads equipment types from Phase 2
2. Queries merged_validation_dataset.csv for UDC evidence
3. Calculates UDC coverage per equipment type
4. Builds equipment hierarchy via Jaccard similarity
5. Consolidates groups with >80% UDC overlap
6. Validates high/medium/low confidence groups
7. Generates ASCII tree to `analytical_output/equipment_hierarchy.txt`
8. Saves results to `summaries.json` under `analysis_udc`

---

## How Phase 2 Feeds Into Phase 3 (UDC Bridging & Validation)

### Phase 3: `udc_bridge_analysis.py`

**Goal**: Validate equipment types using UDC technical evidence and build equipment hierarchy

**Scope**:
1. UDC-Based Validation (technical reality check)
2. Equipment Hierarchy Discovery (build tree structure)
3. Group Refinement (merge similar, flag problematic)

---

### Step 1: UDC-Based Validation

**Process**:
```python
for equipment_type in assumed_equipment_types:
    # Get all facility IDs for this equipment type
    facility_ids = equipment_type["facility_ids"]
    
    # Query PNT dataset (merged_validation_dataset.csv)
    pnt_records = pnt_df[pnt_df["facilityid"].isin(facility_ids)]
    
    # Extract distinct UDCs with usage counts
    udc_analysis = pnt_records.groupby("uniformdatacode").agg({
        "tag": "count",           # How many tags use this UDC
        "description": "first"    # UDC description from TRS
    })
    
    # Calculate coverage (% of facilities using each UDC)
    for udc in udc_analysis:
        facilities_with_udc = pnt_records[pnt_records["uniformdatacode"] == udc]["facilityid"].nunique()
        coverage = facilities_with_udc / len(facility_ids)
        udc_analysis[udc]["coverage"] = coverage
    
    # Build UDC profile for this equipment type
    equipment_type["udc_profile"] = {
        "total_unique_udcs": len(udc_analysis),
        "core_udcs": [udc for udc in udc_analysis if coverage > 0.80],  # 80%+ facilities
        "common_udcs": [udc for udc in udc_analysis if 0.50 < coverage <= 0.80],  # 50-80%
        "optional_udcs": [udc for udc in udc_analysis if coverage <= 0.50]  # <50%
    }
```

**Output for Each Equipment Type**:
```json
{
  "equipment_type_id": 2,
  "suggested_name": "Gas Meters",
  "facility_count": 698,
  "confidence_before": 0.789,
  "confidence_after": 0.98,  // Upgraded by UDC validation
  "udc_profile": {
    "total_unique_udcs": 23,
    "core_udcs": [
      {"udc": "FLOWGAS", "desc": "Gas Flow Rate", "coverage": 0.98, "tag_count": 685},
      {"udc": "PRESSLINE", "desc": "Line Pressure", "coverage": 0.95, "tag_count": 663}
    ],
    "common_udcs": [
      {"udc": "TEMPGAS", "desc": "Gas Temperature", "coverage": 0.67, "tag_count": 468}
    ],
    "optional_udcs": [
      {"udc": "COMPRATIO", "desc": "Compression Ratio", "coverage": 0.45, "tag_count": 314}
    ]
  }
}
```

---

### Step 2: Equipment Hierarchy Discovery

**Method**: Analyze UDC overlap patterns between equipment types

```python
# Build similarity matrix
for type_a in equipment_types:
    for type_b in equipment_types:
        if type_a == type_b:
            continue
        
        # Get UDC sets
        udcs_a = set(type_a["udc_profile"]["core_udcs"])
        udcs_b = set(type_b["udc_profile"]["core_udcs"])
        
        # Calculate Jaccard similarity
        intersection = len(udcs_a & udcs_b)
        union = len(udcs_a | udcs_b)
        similarity = intersection / union if union > 0 else 0
        
        # If >60% overlap, potential parent-child relationship
        if similarity > 0.6:
            # Smaller group is likely child of larger group
            if len(type_a["facility_ids"]) < len(type_b["facility_ids"]):
                type_a["parent"] = type_b["suggested_name"]
            else:
                type_b["parent"] = type_a["suggested_name"]
```

**Output**: Text-based hierarchy tree (saved to `equipment_hierarchy.txt`)

```
Facility Equipment Hierarchy
═══════════════════════════════════════

Metering Equipment (1751 facilities)
├── Core UDCs: FLOWRATE, PRESSLINE, TEMPMEAS
├── Gas Meters (698 facilities) [HIGH confidence: 0.98]
│   ├── UDCs: FLOWGAS, PRESSLINE, TEMPGAS
│   └── Optional: COMPRATIO
├── Flow Meters (1053 facilities) [HIGH confidence: 0.80]
│   ├── UDCs: FLOWRATE, PRESSLINE, TEMPAMB
│   └── Optional: DENSITYMEAS
└── Poll Equipment (417 facilities) [HIGH confidence: 0.72]
    ├── UDCs: FLOWRATE, PRESSLINE, POLLFREQ
    └── Optional: COMMSTATUS

Univ Equipment (1455 facilities) [LOW confidence: 0.35]
├── **NEEDS DEEPER ANALYSIS**
├── UDCs discovered: UNIVID, UNIVTYPE, UNIVCFG
└── Recommendation: Split this group in Phase 4

Tanks/Storage (117 facilities) [HIGH confidence: 0.78]
├── UDCs: TANKLEVEL, TEMPSTORAGE, PRESSVAPOR
└── Optional: VALVEDUMP

...
```

---

### Step 3: Group Consolidation (Threshold-Based Merging)

**Strategy**: If two groups have >80% UDC overlap, merge them

```python
merge_threshold = 0.80

for type_a in equipment_types:
    for type_b in equipment_types:
        if type_a["merged"] or type_b["merged"]:
            continue
        
        udcs_a = set(type_a["udc_profile"]["core_udcs"])
        udcs_b = set(type_b["udc_profile"]["core_udcs"])
        
        overlap = len(udcs_a & udcs_b) / max(len(udcs_a), len(udcs_b))
        
        if overlap > merge_threshold:
            # Merge type_b into type_a (keep larger group name)
            type_a["facility_ids"].extend(type_b["facility_ids"])
            type_a["merged_from"].append(type_b["suggested_name"])
            type_b["merged"] = True
```

**Result**:
- **Before**: 50 groups, 14 equipment type names
- **After**: ~10-12 validated equipment categories with UDC evidence

---

### Step 4: Confidence Level Deep Dives

**High Confidence (42 groups)**: ✓ Validated with UDC profiles
- UDC patterns match semantic keywords
- Coverage >80% for core UDCs
- Ready for Ignition UDT generation

**Medium Confidence (7 groups)**: ⚠ Requires review
- UDC patterns partially match keywords
- Coverage 50-80% for core UDCs
- May need manual naming refinement

**Low Confidence (1 group)**: ⚠ Flag for Phase 4 analysis
- Weak UDC patterns (many optional, few core)
- Coverage <50% or highly diverse UDCs
- Likely needs splitting or is configuration/system type

---

## Phase 2 Script Name: `description_analysis.py`

**Full Path**: `cyg_to_ign/Scripts/heavy_analysis/description_analysis.py`

**Command**: `analyze-descriptions`

---

## Summary: The Analysis Pipeline

```
Phase 1: Attribute Analysis (attribute_analysis.py)
  INPUT: FAC CSV + FAC summary
  OUTPUT: key_attributes + assumed_facility_groups
  DISCOVERS: Which columns matter & natural facility clusters

    ↓

Phase 2: Description Analysis (description_analysis.py)
  INPUT: Phase 1 results + FAC descriptions
  OUTPUT: equipment_vocabulary + assumed_equipment_types
  DISCOVERS: What each group actually represents (semantic meaning)

    ↓

Phase 3: UDC Bridge Analysis (udc_bridge_analysis.py) [REVISED SCOPE]
  INPUT: Phase 2 results + PNT dataset (merged_validation_dataset.csv)
  OUTPUT: 
    - udc_validated_equipment_types (with confidence scores)
    - equipment_hierarchy.txt (tree visualization)
    - group_consolidation_report
  
  DISCOVERS:
    - Technical validation through UDC patterns
    - Equipment hierarchy from UDC overlap analysis
    - Core vs Optional UDCs for each equipment type
  
  ACTIONS:
    ✓ Validate high confidence groups (42) with UDC evidence
    ⚠ Deep dive medium confidence groups (7) - refine or merge
    ⚠ Analyze low confidence groups (1) - flag if no UDC pattern
    ✓ Build hierarchy tree from UDC similarity (Jaccard index)
    ✓ Merge groups with >80% UDC overlap
  
  SAVES: equipment_hierarchy.txt

    ↓

Phase 4: Equipment Function Inference [NEW - MOVED FROM OLD PHASE 3]
  INPUT: Phase 3 UDC profiles + validated equipment types
  OUTPUT: equipment_functional_roles + process_relationships
  
  DISCOVERS:
    - Equipment roles (measurement, control, storage, separation)
    - Process flow relationships (upstream/downstream dependencies)
    - Operational patterns from UDC co-occurrence
    - Likely equipment functions from UDC combinations

    ↓

Phase 5: Tag Pattern Analysis (tag_pattern_analysis.py) [MOVED FROM PHASE 4]
  INPUT: Phase 4 results + tag naming conventions from PNT
  OUTPUT: tag_templates + naming_rules + ignition_udt_structure
  
  DISCOVERS: 
    - Tag naming patterns per equipment type
    - Site prefixes, UDC abbreviations, numbering schemes
    - Ignition UDT template structure for each equipment category
```

---

## Why This Approach Works

### 1. **Each Phase Validates the Previous**
- Attribute patterns → Validated by descriptions (Phase 2)
- Descriptions → Validated by UDC technical evidence (Phase 3)
- UDC profiles → Inform equipment function (Phase 4)
- Functions → Guide tag template generation (Phase 5)

### 2. **Progressive Refinement & Validation**
- **Phase 1**: Discover patterns (attribute fill signatures)
- **Phase 2**: Add meaning (semantic keywords)
- **Phase 3**: Validate technically (UDC evidence)
- **Phase 4**: Infer function (equipment roles)
- **Phase 5**: Generate templates (Ignition UDTs)

### 3. **Human Checkpoints**
- After Phase 1: "Do these facility groupings make sense?"
- After Phase 2: "Are these equipment names accurate?"
- After Phase 3: "Does the hierarchy tree look correct? Do UDC profiles match equipment types?"
- After Phase 4: "Are the inferred equipment functions reasonable?"
- After Phase 5: "Are tag templates ready for Ignition import?"

### 4. **Generic & Single-Site Focused**
- No hardcoded equipment type assumptions
- No cross-company comparisons (each analysis is site-specific)
- Discovers patterns from the data itself
- Company/site-agnostic methodology

---

## Next Steps

1. **Review Phase 1 Output** (run `analyze-attributes`)
2. **Validate Groups** - Do they look reasonable?
3. **Build Phase 2** - Start with keyword extraction
4. **Test on Sample** - Try one or two groups first
5. **Iterate** - Refine based on results
