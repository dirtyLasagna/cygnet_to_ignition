"""
Quick test to show what the merged validation dataset columns look like
"""
from cyg_to_ign.Scripts.validation_utils import create_merged_validation_dataset
from working import cache
from cyg_to_ign.Scripts import common

# Load paths
working_folder = common.getWorkingFolder()
workingJSON_path = working_folder + "\\working.json"
workingJSON = cache.load_workingJSON(workingJSON_path)
parser_filepaths = cache.getParserFilePaths(workingJSON)

# Build file paths
trs_filepath = parser_filepaths["base-path"] + "\\" + parser_filepaths["parse-trs"] + parser_filepaths.get("extension")
pnt_filepath = parser_filepaths["base-path"] + "\\" + parser_filepaths["parse-pnt"] + parser_filepaths.get("extension")
fac_filepath = parser_filepaths["base-path"] + "\\" + parser_filepaths["parse-fac"] + parser_filepaths.get("extension")

print("Creating merged dataset (without saving)...\n")

# Create merged dataset without saving
result = create_merged_validation_dataset(
    trs_filepath=trs_filepath,
    pnt_filepath=pnt_filepath,
    fac_filepath=fac_filepath,
    output_path=None  # Don't save yet
)

if result.get("success"):
    print(f"✓ Merge successful!")
    print(f"  Rows: {result['row_count']}")
    print(f"  Columns: {result['column_count']}")
    print(f"\nMerge Statistics:")
    stats = result['merge_stats']
    print(f"  TRS (filtered ~UDCALL): {stats['trs_filtered_rows']}")
    print(f"  TRS→PNT matched: {stats['trs_pnt_matched']}")
    print(f"  TRS→PNT unmatched: {stats['trs_pnt_unmatched']}")
    
    # Show unmatched TRS entries
    if stats.get('unmatched_trs_count', 0) > 0:
        print(f"\n⚠ ~UDCALL Entries without a PNT uniformdatacode match ({stats['unmatched_trs_count']}):")
        unmatched = stats.get('unmatched_trs_entries', [])
        for entry in unmatched[:15]:  # Show first 15
            print(f"    • {entry}")
        if stats['unmatched_trs_count'] > 15:
            print(f"    ... and {stats['unmatched_trs_count'] - 15} more")
    
    print(f"\nPNT→FAC Join:")
    print(f"  PNT→FAC matched: {stats['pnt_fac_matched']}")
    print(f"  PNT→FAC unmatched: {stats['pnt_fac_unmatched']}")
    
    print(f"\n{'='*80}")
    print(f"MERGED DATASET COLUMNS ({result['column_count']} columns):")
    print(f"{'='*80}\n")
    
    # Display all columns with source indicators
    for i, col in enumerate(result['columns'], 1):
        source = "TRS" if col.startswith('trs_') else ("FAC" if col.startswith('fac_') else "PNT")
        print(f"  {i:2}. [{source}] {col}")
    
    # Show first few rows if available
    if result.get('merged_df') is not None:
        df = result['merged_df']
        print(f"\n{'='*80}")
        print(f"FIRST 5 ROWS (preview):")
        print(f"{'='*80}\n")
        print(df.head(5).to_string(index=False))
    
else:
    print(f"✗ Merge failed: {result.get('error')}")
    if result.get('traceback'):
        print(f"\n{result['traceback']}")
