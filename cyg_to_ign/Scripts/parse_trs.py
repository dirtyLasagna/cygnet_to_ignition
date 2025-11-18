import os
import csv
from pathlib import Path
import pandas as pd

from cyg_to_ign.Scripts.common  import getRootFolder

# ====================================
#   --- functions ---
# ====================================
def getColumnHeaders(file_path: str) -> list:
    
    # Read headers 
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)
    return headers

# ------------------------------------
#  === MAIN ===
# ------------------------------------

def runParseTRS(filename: str) -> dict:
    # Folder and file
    root = getRootFolder()
    input_folder = os.path.join(root, 'cygnet_input')
    file_path = os.path.join(input_folder, f"{filename}.csv")

    # Validate file existence
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in {input_folder}")
    
    # Read headers 
    headers = getColumnHeaders(file_path)

    # Load CSV into pandas for analysis
    df = pd.read_csv(file_path)
    total_rows = len(df)
    
    # non-empty counts and %'s
    non_empty_counts = { col: f"{df[col].notnull().sum()}/{total_rows}" for col in headers}
    percentage_counts = { col: str(float(round((df[col].notnull().sum() / total_rows) * 100, 2))) + "%" for col in headers }
    
    # unique counts 
    distinct_counts = { col: df[col].nunique() for col in headers }
    
    # empty columns classification
    empty_columns = []
    for col in headers:
        empty_ratio = (df[col].isnull().sum() / total_rows) * 100
        if empty_ratio == 100:
            empty_columns.append(f"{col}: Unused (100%)")
        elif empty_ratio > 50: 
            empty_columns.append(f"{col}: Majority Empty ({round(empty_ratio, 2)}%)")
    
    # Missing Values
    missing_values = { col: {
        "Fraction": f"{df[col].isnull().sum()}/{total_rows}",
        "Percent": str(float(round((df[col].isnull().sum() / total_rows) * 100, 2))) + "%"
    } for col in headers }

    # Focus Table (~UDCALL)
    udcall_df = df[df['TABLE'] == '~UDCALL']
    total_udcall_rows = len(udcall_df)
    udcall_focus = {
        "Row Count": len(udcall_df),
        "Percent of Total": round((len(udcall_df) / total_udcall_rows) * 100, 2),
        "Distinct ENTRY": udcall_df['ENTRY'].nunique(),
        "Distinct DESC": udcall_df['DESC'].nunique()
    }

    # Compare basic stats
    summary = {
        "Total Rows": total_rows,
        "Headers": headers,
        "Non Empty Counts Per Column": non_empty_counts,
        "Percentage Count": percentage_counts,
        "Unique Header Count": distinct_counts,
        "Empty Columns": empty_columns,
        "Missing Values": missing_values,
        "Focus TABLE (~UDCALL)": udcall_focus
    }

    return summary