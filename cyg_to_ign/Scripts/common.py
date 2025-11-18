import os
import csv
from pathlib import Path

def getRootFolder() -> str:
    root_folder = str(Path(__file__).resolve().parent.parent.parent)
    return root_folder

