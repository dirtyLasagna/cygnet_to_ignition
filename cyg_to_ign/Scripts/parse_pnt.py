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

    return

def profilePNTFile(file_path: str) -> dict: # row count, missing values, duplicates

    return

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
    return headers