import os
import csv
from pathlib import Path
import pandas as pd

from cyg_to_ign.Scripts.common  import getRootFolder

def getColumnHeaders(file_path: str) -> list:
    # Read headers 
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)
    return headers

def validatePNTFile(file_path: str) -> bool:
    # Check if file exists
    if not os.path.isfile(file_path):
        return False
    
    # Read headers
    headers = getColumnHeaders(file_path)

    # Required columns
    required_cols = ['uniformdatacode', 'description', 'pointdatatype']
    missing_cols = [ col for col in required_cols if col not in headers ]

    if missing_cols:
        print(f"Missing required columns: {', '.join(missing_cols)}")
        return False
    
    return True

def profilePNTFile(file_path: str) -> dict: # row count, missing values, duplicates
    df = pd.read_csv(file_path)
    df.replace(r'^\s*$', pd.NA, regex=True, inplace=True)
    total_rows = len(df)

    full_categories = []
    missing_values = {}
    empty_categories = []

    for col in df.columns:
        missing_count = df[col].isnull().sum()
        missing_percent = round((missing_count / total_rows) * 100, 2)

        # if column has 0 percent missing, separate into "missing"
        if missing_percent < 100 and missing_percent > 0:
            missing_values[col] = {
            "count": int(missing_count),
            "percent": str(missing_percent) + "%" 
        }
            continue
        
        # empty b/c missing count equals total count
        elif missing_count == total_rows:
            empty_categories.append(str(col))
            continue

        # full values
        elif missing_percent == 0:
            full_categories.append(str(col))

    # check for unaccounted columns aka VALIDATE ANALYSIS
    headers = getColumnHeaders(file_path)
    accounted = set(full_categories) | set(missing_values.keys()) | set(empty_categories)
    unaccounted = [ col for col in headers if col not in accounted ]

    summary = {
        "Total Rows": total_rows,
        "Full Rows": full_categories,
        "Missing Values": missing_values,
        "Empty Categories": empty_categories,
        "Unique UDC Count": df['uniformdatacode'].nunique(),
        "Unique Desc Count": df['description'].nunique(),
        "Unaccounted Columns": unaccounted
    }

    return summary

def buildPNTMapping(file_path: str) -> dict: # UDC -> TagName

    return

def crossReferenceTRS_PNT(trs_summary: dict, pnt_mapping: dict) -> dict:

    return

def displayPNTSummary(summary: dict): # Rich Formatting: create a new py file

    return

# MAIN
def runParsePNT(file_name: str):
    # Folder and file
    root = getRootFolder()
    input_folder = os.path.join(root, 'cygnet_input')
    file_path = os.path.join(input_folder, f"{file_name}.csv")

    # Validate file existence
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File '{file_name}' not found in {input_folder}")
    
    # Read headers 
    headers = getColumnHeaders(file_path)
    
    # test
    test = profilePNTFile(file_path)

    # row count, get list of unique 'uniformdatacode' columns

    # mapping preparation

    # duplicate detection

    # subsystem grouping

    # cross-reference w/ TRS 
        # compare udc's in PNT to ENTRY's in TRS w/ ~UDCALL
        # highlight:
            # matches
            # missing mappings
            # extra UDCs not found in TRS
    
    # Human-Readable Mapping
        # UDC | Tagname | TRS Description

    # Pattern Analysis
        # Detect Common naming conventions in PNT tags
        # Compare with TRS prefixes for consistency
    
    # Rich CLI Output
        # Show summary tables for:
            # Match rate
            # Missing Mappings
            # Duplicate issues
    
    # Export Mapping:
        # Allow saving the mapping as CSV or JSON for use

    return test