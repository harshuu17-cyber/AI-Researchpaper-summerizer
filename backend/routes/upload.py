import os
from pathlib import Path
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.pdf_extractor import extract_text_from_pdf


router = APIRouter(
    prefix="/api/paper",
    tags=["Research Paper"]
)


_candidate_roots = [
    Path(__file__).resolve().parents[2],
    Path(__file__).resolve().parent.parent,
]
_default_upload = next((r / "uploads" for r in _candidate_roots if (r / "uploads").exists()), _candidate_roots[0] / "uploads")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(_default_upload)))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    paper_id = f"paper_{uuid.uuid4().hex[:10]}"

    file_path = UPLOAD_DIR / f"{paper_id}.pdf"

    try:

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty."
            )

        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        extracted = extract_text_from_pdf(
            str(file_path)
        )

        if not extracted["full_text"].strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text was found in this PDF."
            )

        return {
            "success": True,
            "paper_id": paper_id,
            "filename": file.filename,
            "page_count": extracted["page_count"],
            "word_count": extracted["word_count"],
            "character_count": extracted["character_count"],
            "text_preview": extracted["full_text"][:2000]
        }

    except HTTPException:

        if file_path.exists():
            file_path.unlink()

        raise

    except Exception as e:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(e)}"
        )