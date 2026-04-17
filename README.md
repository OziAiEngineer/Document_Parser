# Legal Document Extraction Agent

A Python-based AI agent that extracts structured data from unstructured legal and medical documents using Ollama with Mistral 3 running locally.

## Features

- Extracts specific fields from legal documents into validated JSON
- Supports multiple document formats: TXT, PDF, DOCX
- Understands full document context (not just keyword matching)
- Handles various date formats and normalizes to dd/mm/yyyy
- Validates mandatory fields and flags documents for human review
- Uses Pydantic v2 for robust data validation
- Works with locally-hosted Ollama (no API keys required)

## Prerequisites

- Python 3.11 or higher
- Ollama installed and running locally

## Installation

### 1. Install Ollama

Visit [https://ollama.ai](https://ollama.ai) and follow the installation instructions for your operating system.

For most systems:
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download and run the installer from ollama.ai
```

### 2. Pull the Mistral Model

```bash
ollama pull mistral
```

### 3. Start Ollama Server

```bash
ollama serve
```

The server will run on `http://localhost:11434` by default.

### 4. Install Python Dependencies

```bash
cd legal_extractor
pip install -r requirements.txt
```

## Usage

### Basic Execution

The agent supports TXT, PDF, and DOCX formats:

```bash
# Text file
python main.py sample_documents/sample_1.txt

# PDF file
python main.py documents/legal_case_001.pdf

# Word document
python main.py documents/medical_report.docx
```

### Expected Output

The agent will output a validated JSON object with extracted fields:

```json
{
  "case_instructing_party": {
    "agency_ref": "PLS-2023-891",
    "agency_name": "Premier Legal Services Ltd",
    "instructor_reference": "INS-JM-445",
    "instructing_party": "Johnson & Matthews Solicitors"
  },
  "claimant_details": {
    "title": "Mr",
    "forenames": "John David",
    "surname": "Smith",
    "postcode": "B12 9QR",
    "address": "42 Oak Avenue, Birmingham, B12 9QR",
    "email": "j.smith@email.com",
    "medco_reference_no": "MEDCO-2023-7845",
    "gender": "Male",
    "date_of_birth": "15/08/1985",
    "telephone_home": "0121 555 0123",
    "telephone_work": "0121 555 9876",
    "mobile": "07700 900123",
    "cnf_claim_submission_date": "18/04/2023"
  },
  "case_status_tracking": {
    "urn": "URN-2023-04567",
    "status": "Active"
  },
  "accident_and_expert": {
    "accident_date": "12/04/2023",
    "expert_name": "Dr. Sarah Williams",
    "source": "Hospital Emergency Department"
  },
  "medical_records": {
    "records_required": true,
    "records_arrived": true,
    "arrived_date": "20/04/2023"
  },
  "special_instructions": {
    "injuries_symptoms": "Whiplash injury to cervical spine, lower back pain (lumbar region), bruising to left shoulder, minor cuts and abrasions to hands. Ongoing neck stiffness and reduced mobility in lower back with moderate pain levels affecting daily activities."
  },
  "requires_human_review": false,
  "missing_mandatory_fields": []
}
```

## Testing with Sample Documents

### Sample 1 (Structured Format)
```bash
python main.py sample_documents/sample_1.txt
```
This document has clearly labeled fields and should extract all data successfully.

### Sample 2 (Narrative Format)
```bash
python main.py sample_documents/sample_2.txt
```
This document is written in narrative prose style, testing the agent's ability to understand context and extract information from natural language.

## Extraction Schema

The agent extracts the following fields:

- **Case Instructing Party**: Agency details, references, instructing party
- **Claimant Details**: Name, contact info, demographics, references
- **Case Status Tracking**: URN, status
- **Accident and Expert**: Accident date, expert name, source
- **Medical Records**: Required/arrived status, dates
- **Special Instructions**: Injuries and symptoms (full description)

## Validation Rules

### Mandatory Fields
- `claimant_details.surname`
- `accident_and_expert.accident_date`

If either mandatory field is missing, the output will include:
```json
{
  "requires_human_review": true,
  "missing_mandatory_fields": ["claimant_details.surname"]
}
```

### Data Rules
- Dates are normalized to `dd/mm/yyyy` format
- Gender is inferred from title if not explicitly stated (Mr = Male, Mrs/Miss/Ms = Female)
- Missing fields return `null` (never hallucinated)
- Injuries/symptoms are extracted from full document context

## Project Structure

```
legal_extractor/
├── main.py              # Entry point - accepts document file path
├── agent.py             # Core extraction logic - calls Ollama
├── document_parser.py   # Multi-format document parser (TXT/PDF/DOCX)
├── schema.py            # Pydantic v2 models for all fields
├── validator.py         # Checks mandatory fields, flags for review
├── prompt_builder.py    # Builds system + user prompts
├── utils.py             # Date normalization, text cleaning
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── sample_documents/
    ├── sample_1.txt     # Clearly formatted document
    └── sample_2.txt     # Narrative paragraph-style document
```

## Troubleshooting

### Ollama Connection Error
```
Failed to connect to Ollama: Connection refused
```
**Solution**: Ensure Ollama is running with `ollama serve`

### Model Not Found
```
Error: model 'mistral' not found
```
**Solution**: Pull the model with `ollama pull mistral`

### PDF Support Missing
```
ImportError: PDF parsing requires 'pypdf' library
```
**Solution**: Install PDF support with `pip install pypdf`

### DOCX Support Missing
```
ImportError: DOCX parsing requires 'python-docx' library
```
**Solution**: Install DOCX support with `pip install python-docx`

### Poor PDF Text Extraction
Some PDFs (especially scanned documents) may not extract text properly. For scanned PDFs, you'll need OCR:
```bash
pip install pytesseract pillow pdf2image
```
Then use an OCR preprocessing step (not included in this version).

### Slow Extraction
The first run may be slow as Ollama loads the model into memory. Subsequent runs will be faster.

## Document Format Support

### Supported Formats

| Format | Status | Library | Notes |
|--------|--------|---------|-------|
| TXT | ✓ Supported | Built-in | Plain text files |
| PDF | ✓ Supported | pypdf | Extracts text from digital PDFs |
| DOCX | ✓ Supported | python-docx | Microsoft Word documents |

### Format-Specific Notes

**PDF Files:**
- Works best with digital PDFs (text-based)
- Scanned PDFs require OCR (not included)
- Extracts text from all pages
- Handles tables and multi-column layouts

**DOCX Files:**
- Extracts paragraphs and tables
- Preserves document structure
- Compatible with .docx format (not legacy .doc)

**TXT Files:**
- Direct text reading
- UTF-8 encoding with fallback

## Future Enhancements

- OCR support for scanned PDFs (using pytesseract)
- Excel output integration (using openpyxl)
- Batch processing of multiple documents
- Web interface for document upload
- Fine-tuning prompts for specific document types
- Support for legacy .doc format (using python-docx2txt)

## License

MIT License - feel free to use and modify for your needs.
