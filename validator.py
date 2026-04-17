"""Validation logic for extracted data."""
from typing import Dict, Any, List, Tuple
from schema import LegalDocumentExtraction


class ExtractionValidator:
    """Validates extracted data and flags missing mandatory fields."""
    
    MANDATORY_FIELDS = [
        ("claimant_details", "surname"),
        ("tracking_and_administration", "accident_date")
    ]
    
    def validate(self, extracted_data: Dict[str, Any]) -> Tuple[LegalDocumentExtraction, bool]:
        """
        Validate extracted data against schema and check mandatory fields.
        
        Args:
            extracted_data: Raw dictionary from LLM
            
        Returns:
            Tuple of (validated model, needs_review flag)
        """
        # Parse with Pydantic
        model = LegalDocumentExtraction(**extracted_data)
        
        # Check mandatory fields
        missing_fields = self._check_mandatory_fields(model)
        
        if missing_fields:
            model.requires_human_review = True
            model.missing_mandatory_fields = missing_fields
        
        return model, model.requires_human_review
    
    def _check_mandatory_fields(self, model: LegalDocumentExtraction) -> List[str]:
        """Check if mandatory fields are present."""
        missing = []
        
        for section, field in self.MANDATORY_FIELDS:
            section_obj = getattr(model, section)
            value = getattr(section_obj, field)
            
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(f"{section}.{field}")
        
        return missing
