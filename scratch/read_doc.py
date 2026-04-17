import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(r"c:\Users\appwing\Desktop\agenticai\legal_extractor")

from utils import read_document

file_path = r"c:\Users\appwing\Desktop\agenticai\legal_extractor\extracted_files\W2580591\Letter of Instruction from Solicitor.DOC"
try:
    text = read_document(file_path)
    print("--- DOCUMENT TEXT START ---")
    print(text)
    print("--- DOCUMENT TEXT END ---")
except Exception as e:
    print(f"Error: {e}")
