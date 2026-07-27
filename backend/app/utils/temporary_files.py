import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile

# Point to backend/temporary_data
TEMP_DIR = Path(__file__).resolve().parent.parent.parent / "temporary_data"

def ensure_temp_dir() -> None:
    """
    Ensures that the temporary data directory exists.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

def save_temporary_file(file: UploadFile, ext: str) -> str:
    """
    Saves an UploadFile object to the temporary directory.
    Returns the absolute path to the saved file.
    """
    ensure_temp_dir()
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    dest_path = TEMP_DIR / filename
    
    file.file.seek(0)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return str(dest_path)

def delete_temporary_file(file_path: str) -> None:
    """
    Deletes a local temporary file safely.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        # Suppress errors to ensure operations don't block
        pass

def clean_all_temporary_files() -> None:
    """
    Deletes all files in the temporary directory.
    """
    if os.path.exists(TEMP_DIR):
        for item in os.listdir(TEMP_DIR):
            item_path = TEMP_DIR / item
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception:
                pass
