import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import main processing logic
from main import run_service
from folder_processor import SUPPORTED_EXTENSIONS

app = FastAPI(title="Legal Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static and output directories exist
os.makedirs("static", exist_ok=True)

# Mount static files (for UI)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

def _detect_folder_structure(folder_path: str, company: str) -> str:
    path = Path(folder_path)
    
    # Check for subfolders with docs (Speed batch style)
    has_subfolders_with_docs = False
    try:
        for sub in path.iterdir():
            if sub.is_dir() and not sub.name.startswith("."):
                # Check for docs in this subfolder
                for f in sub.iterdir():
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                        has_subfolders_with_docs = True
                        break
            if has_subfolders_with_docs: break
    except Exception:
        pass
        
    if has_subfolders_with_docs:
        return "folder"
        
    if company.lower() == "mla":
        return "folder"
        
    return "single"


@app.post("/api/extract")
async def extract_data(
    company: str = Form(...),
    files: List[UploadFile] = File(...),
    paths: Optional[str] = Form(None)
):
    try:
        extract_path = Path("extracted_files")
        
        # Clean previous extraction
        if extract_path.exists():
            shutil.rmtree(extract_path)
            
        extract_path.mkdir(parents=True, exist_ok=True)
        
        # Reconstruct path mapping from comma-separated string if provided
        path_list = paths.split(",") if paths else []
        
        is_zip = len(files) == 1 and files[0].filename.lower().endswith('.zip')

        if is_zip:
            # It's a ZIP file, extract it
            zip_dest = extract_path / files[0].filename
            with open(zip_dest, "wb") as f:
                f.write(await files[0].read())
                
            with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
                zip_ref.extractall(path=extract_path, pwd=b"smes")
                
            os.remove(zip_dest)
            target_path = str(extract_path)
            
        else:
            # We have one or multiple standard files
            for i, file_obj in enumerate(files):
                rel_path = path_list[i] if i < len(path_list) and path_list[i] else file_obj.filename
                # Ensure no crazy relative path attacks
                safe_rel_path = rel_path.lstrip("/\\")
                dest_file = extract_path / safe_rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(dest_file, "wb") as f:
                    f.write(await file_obj.read())
                    
        target_path_obj = extract_path
        # Collapse redundant top-level directories (e.g. if the upload was a folder 'W2588062' containing files, it shouldn't process the parent 'extracted_files' which would fail to find files directly)
        while True:
            top_level = list(target_path_obj.iterdir())
            if len(top_level) == 1 and top_level[0].is_dir():
                target_path_obj = top_level[0]
            else:
                break
                
        target_path = str(target_path_obj)
        
        # Detect mode
        current_mode = _detect_folder_structure(target_path, company)
        
        # If it's 'single' mode and target_path is a directory, supply a list of files
        target_input = target_path
        if current_mode == "single" and os.path.isdir(target_path):
            docs = []
            for p in Path(target_path).rglob("*"):
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                    docs.append(str(p))
            # Main accepts a list of docs
            if len(docs) == 0:
                raise Exception("No supported documents found in the uploaded directory.")
            target_input = docs

        # Call Main Service
        results = run_service(   
            mode=current_mode,
            target_path=target_input,
            company=company.lower(),
            excel=True
        )

        return JSONResponse(content={"status": "success", "results": results})

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
