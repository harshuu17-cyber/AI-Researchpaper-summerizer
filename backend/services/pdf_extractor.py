import pymupdf
from pathlib import Path


def extract_text_from_pdf(pdf_path: str):
    """
    Extract text from a PDF using PyMuPDF.
    """

    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    pages = []
    full_text_parts = []

    document = pymupdf.open(pdf_path)

    try:
        for page_number, page in enumerate(document, start=1):

            text = page.get_text("text") or ""
            text = text.strip()

            pages.append({
                "page": page_number,
                "text": text
            })

            if text:
                full_text_parts.append(text)

    finally:
        document.close()

    complete_text = "\n\n".join(full_text_parts)

    return {
        "pages": pages,
        "page_count": len(pages),
        "word_count": len(complete_text.split()),
        "character_count": len(complete_text),
        "full_text": complete_text
    }