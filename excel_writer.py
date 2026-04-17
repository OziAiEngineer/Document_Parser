"""
Excel Writer — bridges the extraction models and the Excel template.
"""
from typing import List, Dict, Any
from schema import LegalDocumentExtraction
from excel_exporter import ExcelExporter
import os
import shutil

def write_to_excel(results: List[Dict[str, Any]], output_file: str):
    """
    Takes a list of extraction dictionaries, validates them,
    and writes them all to the specified Excel file.
    """
    if not results:
        return

    # Use the existing template logic
    template_path = "output/Import Template.xlsx"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Copy template to the target location first if it doesn't exist
    if not os.path.exists(output_file):
        if os.path.exists(template_path):
            shutil.copy(template_path, output_file)
        else:
            # If template is missing, we have a problem, but let exporter handle it
            pass

    exporter = ExcelExporter(template_path=output_file)
    
    for result in results:
        # Create a copy so we don't modify the original during metadata stripping
        data = result.copy()
        # Remove private metadata keys before validation if they exist
        data.pop("_case_metadata", None)
        
        try:
            # Validate into model
            model = LegalDocumentExtraction(**data)
            # Export to the provided file path
            exporter.export(model)
        except Exception as e:
            print(f"Skipping Excel row for a case due to validation error: {e}")
