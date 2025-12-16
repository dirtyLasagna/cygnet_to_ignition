import os 
import csv
import pandas as pd
from datetime import datetime

from typing import Dict, Any
from cyg_to_ign.Scripts import common

def runParseFAC(csv_name: str) -> Dict[str, Any]:
    # Parse FAC export. Create and Return a summary dictionary.
    # Focus: facility IDs, attributes, equipment mapping prep.

    # Build filepath
    base_path = common.getRootFolder() + "\\cygnet_input\\"
    csv_path = base_path + csv_name + ".csv"

    if not os.path.exists(csv_path):
        return {"error": f"File not found: {csv_path}"}
    
    # Read CSV
    df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)

    # Basic stats
    total_rows = len(df)
    headers = df.columns.tolist()

    # Initialize analysis structures
    non_empty_counts = {}
    percentage_counts = {}
    unique_counts = {}
    missing_values = {}
    full_columns = []  # 100% populated
    empty_columns = []  # 100% empty
    mixed_columns = []  # > 90% empty

    # Analyze each column
    for col in headers:
        # Count non-empty values (convert to native Python int for JSON serialization)
        non_empty = int(df[col].notna().sum())
        missing = int(total_rows - non_empty)
        
        # Calculate percentages
        percent_filled = (non_empty / total_rows * 100) if total_rows > 0 else 0
        percent_missing = (missing / total_rows * 100) if total_rows > 0 else 0
        
        # Store counts
        non_empty_counts[col] = f"{non_empty}/{total_rows}"
        percentage_counts[col] = f"{percent_filled:.2f}%"
        
        # Unique values (only for non-empty, convert to native Python int)
        unique_counts[col] = int(df[col].nunique())
        
        # Missing values detail
        missing_values[col] = {
            "count": missing,
            "percent": f"{percent_missing:.2f}%"
        }
        
        # Categorize columns
        if percent_filled == 100:
            full_columns.append(col)
        elif percent_filled == 0:
            empty_columns.append(f"{col}: Unused (100% empty)")
        elif percent_missing > 0 and percent_missing < 100:
            mixed_columns.append(f"{col}: Partially Empty ({percent_missing:.2f}%)")

    # Filter missing values to only show columns with missing data
    missing_values_filtered = {
        col: val for col, val in missing_values.items() 
        if val["count"] > 0
    }

    # Focus on key columns (site, service, id, type, desc, category)
    key_columns = ['site', 'service', 'id', 'is_active', 'type', 'desc', 'category']
    key_column_stats = {}
    for col in key_columns:
        if col in headers:
            key_column_stats[col] = {
                "Unique Values": unique_counts.get(col, 0),
                "Non-Empty": non_empty_counts.get(col, "N/A"),
                "Filled Percent": percentage_counts.get(col, "N/A")
            }

    # Build summary dict
    summary = {
        "Total Rows": total_rows,
        "Headers": headers,
        "Non Empty Counts Per Column": non_empty_counts,
        "Percentage Filled": percentage_counts,
        "Unique Counts": unique_counts,
        "Missing Values": missing_values_filtered,
        "Full Columns": full_columns,
        "Empty Columns": empty_columns,
        "Partially Empty Columns": mixed_columns,
        "Key Column Statistics": key_column_stats,
        "Column Summary": {
            "Total Columns": len(headers),
            "Fully Populated": len(full_columns),
            "Fully Empty": len(empty_columns),
            "Partially Filled": len(headers) - len(full_columns) - len(empty_columns)
        },
        "_meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "unix_ts": int(datetime.now().timestamp()),
            "source": "fac_summary",
            "filepath": csv_path
        }
    }

    return summary