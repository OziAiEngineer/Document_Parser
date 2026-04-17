import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(r"c:\Users\appwing\Desktop\agenticai\legal_extractor")

from utils import read_document

file_path = r"c:\Users\appwing\Desktop\agenticai\legal_extractor\extracted_files\W2580591\Letter of Instruction from Solicitor.DOC"
try:
    text = read_document(file_path)
    print(f"Total characters: {len(text)}")
    print("--- FIRST 500 CHARS ---")
    print(text[:500])
    print("---")
    
    # Try the other doc too
    file_path2 = r"c:\Users\appwing\Desktop\agenticai\legal_extractor\extracted_files\W2580591\Letter of Instruction to Expert.doc"
    text2 = read_document(file_path2)
    print(f"Total characters (Doc 2): {len(text2)}")
    print("--- FIRST 500 CHARS (Doc 2) ---")
    print(text2[:500])
    print("---")
    
except Exception as e:
    print(f"Error: {e}")
