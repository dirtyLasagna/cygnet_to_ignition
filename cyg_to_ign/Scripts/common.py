import os
import csv
from pathlib import Path

def getRootFolder() -> str:
    root_folder = str(Path(__file__).resolve().parent.parent.parent)
    return root_folder

def getSummaryPath() -> str:
    summaries_path = os.path.join("analytical_output", "summaries.json")
    return summaries_path
 