import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_file(upload_file: UploadFile) -> str:
    unique_filename = f"{uuid.uuid4()}_{upload_file.filename}"
    file_path = UPLOAD_DIR / unique_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return str(file_path)


def delete_file(file_path: str):
    path = Path(file_path)
    if path.exists():
        path.unlink()
