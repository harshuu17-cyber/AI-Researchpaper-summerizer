import os
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.pdf_extractor import extract_text_from_pdf
from services.ai_analyzer import analyze_research_paper
from services.data_extractor import extract_numerical_results
from services.chart_selector import select_charts
from services.export_service import (
    ensure_summary_files,
    generate_markdown_summary,
    generate_text_summary,
    generate_pdf_summary_file,
)


router = APIRouter(
    prefix="/api/paper",
    tags=["Research Paper Analysis"]
)


_candidate_roots = [
    Path(__file__).resolve().parents[2],
    Path(__file__).resolve().parent.parent,
]
_default_upload = next((r / "uploads" for r in _candidate_roots if (r / "uploads").exists()), _candidate_roots[0] / "uploads")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(_default_upload)))

_default_outputs = next((r / "outputs" for r in _candidate_roots if (r / "outputs").exists()), _candidate_roots[0] / "outputs")
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", str(_default_outputs)))
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze/{paper_id}")
async def analyze_paper(paper_id: str):

    pdf_path = UPLOAD_DIR / f"{paper_id}.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Paper not found: {paper_id}"
        )

    try:

        # -----------------------------------------
        # STEP 1: Extract PDF text
        # -----------------------------------------

        extracted = extract_text_from_pdf(
            str(pdf_path)
        )

        full_text = extracted["full_text"]

        if not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in the paper."
            )

        # -----------------------------------------
        # STEP 2: AI research-paper analysis
        # -----------------------------------------

        analysis = analyze_research_paper(
            full_text,
            pages=extracted.get("pages", [])
        )

        # -----------------------------------------
        # STEP 3: Extract numerical results
        # -----------------------------------------

        numerical_results = extract_numerical_results(
            full_text
        )

        # -----------------------------------------
        # STEP 4: Select charts automatically
        # -----------------------------------------

        chart_data = select_charts(
            numerical_results
        )

        # -----------------------------------------
        # STEP 5: Return complete result
        # -----------------------------------------

        payload = {
            "success": True,

            "paper_id": paper_id,

            "page_count": extracted["page_count"],

            "word_count": extracted["word_count"],

            "analysis": analysis,

            "numerical_results": numerical_results,

            "charts": chart_data
        }

        # Save summary files (MD, TXT, PDF, JSON) to outputs directory for download/export
        try:
            ensure_summary_files(paper_id, payload, OUTPUTS_DIR)
        except Exception as save_err:
            print(f"[ResearchLens] Warning: Failed to save outputs: {save_err}")

        return payload

    except HTTPException:
        raise

    except Exception as e:
        error_msg = str(e).strip()
        status_code = 500

        # Map known operational errors to appropriate HTTP status codes
        if "rate limit" in error_msg.lower():
            status_code = 429
        elif "too large" in error_msg.lower() or "token limit" in error_msg.lower():
            status_code = 413
        elif "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            status_code = 401

        raise HTTPException(
            status_code=status_code,
            detail=f"Paper analysis failed: {error_msg}"
        )


@router.get("/sample")
async def get_sample_analysis():
    """
    Returns a pre-analyzed sample paper for instant UI testing and demonstration.
    """
    sample_files = sorted(list(OUTPUTS_DIR.glob("*_data.json")))
    if sample_files:
        with open(sample_files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(
        status_code=404,
        detail="No sample paper analysis available."
    )


@router.get("/result/{paper_id}")
async def get_paper_result(paper_id: str):
    """
    Retrieve previously processed paper analysis results by paper ID.
    """
    json_path = OUTPUTS_DIR / f"{paper_id}_data.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(
        status_code=404,
        detail=f"Results not found for paper ID: {paper_id}"
    )


@router.get("/download/{paper_id}")
async def download_summary(paper_id: str, format: str = "pdf"):
    """
    Download the generated summary file for a processed paper.
    Supports format='pdf' (PDF document), format='md' (Markdown summary),
    format='txt' (Plain text), and format='json' (Full analytical data).
    """
    fmt = format.lower().strip()
    if fmt not in ["pdf", "md", "txt", "json"]:
        fmt = "pdf"

    json_path = OUTPUTS_DIR / f"{paper_id}_data.json"
    target_path = None
    if fmt == "json":
        target_path = json_path
    elif fmt == "pdf":
        target_path = OUTPUTS_DIR / f"{paper_id}_summary.pdf"
    elif fmt == "txt":
        target_path = OUTPUTS_DIR / f"{paper_id}_summary.txt"
    else:
        target_path = OUTPUTS_DIR / f"{paper_id}_summary.md"

    # If the requested format file is missing, try to generate it on-the-fly from saved JSON
    if (not target_path.exists() or target_path.stat().st_size == 0) and json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                saved_payload = json.load(f)
            ensure_summary_files(paper_id, saved_payload, OUTPUTS_DIR)
        except Exception as gen_err:
            print(f"[ResearchLens] Warning: Failed to regenerate file on download: {gen_err}")

    if not target_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Summary file not found for paper: {paper_id}. Please analyze the paper first."
        )

    # Create safe academic filename
    paper_title = "paper"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                p_data = json.load(f)
                paper_title = p_data.get("analysis", {}).get("title", "paper")
        except Exception:
            pass

    safe_title = "".join(c if c.isalnum() else "_" for c in paper_title.lower()).strip("_")
    safe_title = safe_title[:45] or "paper"

    media_types = {
        "pdf": "application/pdf",
        "md": "text/markdown; charset=utf-8",
        "txt": "text/plain; charset=utf-8",
        "json": "application/json; charset=utf-8"
    }

    extensions = {
        "pdf": "pdf",
        "md": "md",
        "txt": "txt",
        "json": "json"
    }

    filename = f"{safe_title}_summary.{extensions[fmt]}" if fmt != "json" else f"{safe_title}_analysis.json"

    return FileResponse(
        path=str(target_path),
        media_type=media_types[fmt],
        filename=filename
    )