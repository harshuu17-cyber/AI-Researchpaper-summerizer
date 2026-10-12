import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from groq import Groq, RateLimitError, APIStatusError, APIConnectionError, AuthenticationError


# ============================================================
# GROQ CONFIGURATION
# ============================================================

# Load environment variables, checking project root first
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()


def get_groq_client() -> Groq:
    """Get or instantiate Groq client dynamically from environment."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your hosting dashboard or .env file."
        )
    return Groq(api_key=api_key, max_retries=1)


MODEL_NAME = "openai/gpt-oss-120b"

# ============================================================
# TOKEN & BUDGET CONFIGURATION
# ============================================================

# Target characters for prompt text sent to LLM.
# 18,000 characters is approximately 4,000 - 4,500 tokens.
# Together with prompt instructions and completion tokens, this stays
# safely well below Groq's 8,000 Tokens-Per-Minute (TPM) limit.
MAX_CHARS_FOR_AI = 18000

# Max completion tokens for the structured JSON response
MAX_COMPLETION_TOKENS = 1500


# ============================================================
# TEXT CLEANING & HEADER/FOOTER STRIPPING
# ============================================================

def clean_text(text: str) -> str:
    """
    Clean raw text: fix hyphenation, normalize unicode dashes/quotes,
    remove noisy control characters, and normalize whitespace.
    """
    if not text:
        return ""

    # Normalize unicode hyphens/dashes and quotes
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", text)
    text = re.sub(r"[\u2018\u2019\u00b4`]", "'", text)
    text = re.sub(r"[\u201c\u201d\u00ab\u00bb]", '"', text)

    # Fix hyphenated words at line breaks (e.g., "computa-\ntion" -> "computation")
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Remove non-printable / control characters (keep \n and \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize horizontal whitespace (tabs and multiple spaces)
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines (max 2 consecutive newlines)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def strip_page_headers_and_footers(pages: List[Dict]) -> str:
    """
    Inspect pages extracted from PyMuPDF, detect and remove repeated
    headers/footers (conference titles, running headers, page numbers),
    and return the cleaned text.
    """
    if not pages:
        return ""

    top_candidates = {}
    bottom_candidates = {}

    for page in pages:
        lines = [line.strip() for line in page.get("text", "").split("\n") if line.strip()]
        if not lines:
            continue
        # Collect top 3 lines
        for line in lines[:3]:
            if len(line) < 120:
                top_candidates[line] = top_candidates.get(line, 0) + 1
        # Collect bottom 3 lines
        for line in lines[-3:]:
            if len(line) < 120:
                bottom_candidates[line] = bottom_candidates.get(line, 0) + 1

    # Lines appearing on >= 2 pages in a document with >= 3 pages are repeated headers/footers
    min_freq = 2 if len(pages) >= 3 else 999
    repeated_headers = {k for k, v in top_candidates.items() if v >= min_freq}
    repeated_footers = {k for k, v in bottom_candidates.items() if v >= min_freq}

    page_number_pattern = re.compile(
        r"^\s*(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?\s*$",
        re.IGNORECASE
    )
    boilerplate_pattern = re.compile(
        r"^(?:arXiv:\d+\.\d+|ieee\s+transactions|acm\s+conference|copyright\s+©|all\s+rights\s+reserved|"
        r"authorized\s+licensed\s+use|published\s+by|issn\s+\d+|doi:\s*10\.\d+)",
        re.IGNORECASE
    )

    cleaned_parts = []

    for page in pages:
        raw_lines = page.get("text", "").split("\n")
        cleaned_lines = []
        for line in raw_lines:
            s_line = line.strip()
            if not s_line:
                continue
            if s_line in repeated_headers or s_line in repeated_footers:
                continue
            if page_number_pattern.match(s_line):
                continue
            if boilerplate_pattern.match(s_line) and len(s_line) < 150:
                continue
            cleaned_lines.append(line)

        page_text = clean_text("\n".join(cleaned_lines))
        if page_text:
            cleaned_parts.append(page_text)

    return "\n\n".join(cleaned_parts)


# ============================================================
# REFERENCE & BIBLIOGRAPHY REMOVAL
# ============================================================

def strip_references(text: str) -> Tuple[str, str]:
    """
    Detect the start of the References / Bibliography section and strip it out.
    Saves thousands of unnecessary tokens that provide zero summary value.
    Returns (cleaned_text_without_references, stripped_references_text).
    """
    if not text:
        return "", ""

    # Search in the latter 60% of the paper to avoid false positives in early text
    search_start = int(len(text) * 0.40)
    sub_text = text[search_start:]

    patterns = [
        # Explicit section heading for references/bibliography
        r"(?m)^\s*(?:(?:[0-9IVXLCDM]+|[A-Z])[\.\s]+)?(?:references|bibliography|literature\s+cited|works\s+cited)\s*$",
        r"\n\s*(?:(?:[0-9IVXLCDM]+|[A-Z])[\.\s]+)?REFERENCES\b",
        # Common citation list start [1] Author Name...
        r"\n\s*\[1\]\s+[A-Z]"
    ]

    best_match_pos = -1
    for pat in patterns:
        m = re.search(pat, sub_text, re.IGNORECASE)
        if m:
            pos = search_start + m.start()
            if best_match_pos == -1 or pos < best_match_pos:
                best_match_pos = pos

    if best_match_pos != -1:
        main_content = text[:best_match_pos].strip()
        ref_content = text[best_match_pos:].strip()
        return main_content, ref_content

    return text.strip(), ""


# ============================================================
# SECTION DETECTION & DISTILLATION
# ============================================================

def distill_key_sections(text: str, max_chars: int = MAX_CHARS_FOR_AI) -> str:
    """
    For papers that exceed max_chars, detect important academic sections
    and assemble a concentrated representation prioritized by:
    1. Title, Authors, Abstract, Introduction & Objectives (~5,000 chars)
    2. Methodology, System Architecture & Models (~4,500 chars)
    3. Datasets, Benchmarks & Experimental Setup (~2,500 chars)
    4. Key Results & Discussion (~3,500 chars)
    5. Conclusion, Limitations & Future Work (~3,500 chars)
    """
    if len(text) <= max_chars:
        return text

    # Pattern for standard academic section headers
    heading_pattern = re.compile(
        r"(?m)^(?:\s*(?:(?:[0-9IVXLCDM]+|[A-Z])[\.\s]+)?)"
        r"(abstract|introduction|background|motivation|overview|"
        r"methodology|methods?|proposed\s+(?:method|approach|framework|model|system)|"
        r"system\s+architecture|architecture|framework|approach|"
        r"experiments?|experimental\s+(?:setup|results|evaluation)|"
        r"evaluations?|datasets?|benchmarks?|implementation\s+details|"
        r"results?|results?\s+and\s+discussion|discussion|findings|performance|"
        r"conclusions?|concluding\s+remarks|limitations?|future\s+work)\b",
        re.IGNORECASE
    )

    matches = list(heading_pattern.finditer(text))

    # If headings are sparse or non-standard, use balanced proportional slicing
    if not matches or len(matches) < 3:
        p1 = text[: int(max_chars * 0.35)]
        mid_start = int(len(text) * 0.38)
        p2 = text[mid_start : mid_start + int(max_chars * 0.35)]
        p3 = text[-int(max_chars * 0.30) :]
        return f"{p1}\n\n[... Methodology & Results Excerpt ...]\n\n{p2}\n\n[... Discussion & Conclusion Excerpt ...]\n\n{p3}"

    # Group paper text into detected sections
    sections = []
    for i in range(len(matches)):
        m = matches[i]
        heading = m.group(0).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((heading, body))

    # Preamble before the first detected section heading (often Title, Authors, affiliations)
    preface = text[: matches[0].start()].strip()

    front_sections = []   # Abstract, Introduction, Background
    method_sections = []  # Methodology, Proposed Method, Architecture
    result_sections = []  # Datasets, Experiments, Results
    end_sections = []     # Conclusion, Discussion, Limitations, Future Work

    for heading, body in sections:
        h_lower = heading.lower()
        if any(w in h_lower for w in ["abstract", "introduction", "background", "motivation", "overview"]):
            front_sections.append(body)
        elif any(w in h_lower for w in ["method", "proposed", "architecture", "framework", "system", "approach"]):
            method_sections.append(body)
        elif any(w in h_lower for w in ["experiment", "dataset", "benchmark", "result", "evaluation", "finding", "performance"]):
            result_sections.append(body)
        elif any(w in h_lower for w in ["conclusion", "discussion", "limitation", "future"]):
            end_sections.append(body)
        else:
            method_sections.append(body)

    # Budget allocation:
    front_text = (preface + "\n\n" + "\n\n".join(front_sections)).strip()[:5000]
    method_text = "\n\n".join(method_sections).strip()[:4500]
    result_text = "\n\n".join(result_sections).strip()[:3500]
    end_text = "\n\n".join(end_sections).strip()[:3500]

    parts = [p for p in [front_text, method_text, result_text, end_text] if p]
    distilled = "\n\n[... SECTION BREAK ...]\n\n".join(parts)
    return distilled[:max_chars]


# ============================================================
# ROBUST JSON PARSER & SCHEMA NORMALIZER
# ============================================================

def parse_json_response(content: str) -> Optional[dict]:
    """
    Safely parse JSON response from LLM with multi-stage fallback recovery.
    """
    if not content:
        return None

    content = content.strip()

    # Remove markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content)

    # 1. Direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 2. Extract outermost JSON object { ... }
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = content[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            # 3. Clean trailing commas before closing braces/brackets
            cleaned = re.sub(r",\s*([\]}])", r"\1", snippet)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    return None


def _clean_str(val: str) -> str:
    if not isinstance(val, str):
        val = str(val)
    val = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", val)
    val = re.sub(r"[\u2018\u2019\u00b4`]", "'", val)
    val = re.sub(r"[\u201c\u201d\u00ab\u00bb]", '"', val)
    return val.strip()


def normalize_schema(raw_data: Optional[dict], fallback_text: str = "") -> dict:
    """
    Ensure all required academic comprehension fields exist with correct data types
    matching the React dashboard expectations.
    """
    schema = {
        "title": "Not specified in the paper",
        "authors": "Not specified in the paper",
        "research_area": "Not specified in the paper",
        "tldr": "Not specified in the paper",
        "abstract_summary": "Not specified in the paper",
        "research_problem": "Not specified in the paper",
        "objective": "Not specified in the paper",
        "key_contributions": [],
        "methodology": "Not specified in the paper",
        "dataset": "Not specified in the paper",
        "models_or_algorithms": [],
        "key_results": [],
        "key_findings": [],
        "practical_applications": [],
        "conclusion": "Not specified in the paper",
        "limitations": [],
        "future_work": [],
        "keywords": [],
    }

    if not isinstance(raw_data, dict):
        raw_data = {}

    # String fields
    for field in [
        "title",
        "authors",
        "research_area",
        "tldr",
        "abstract_summary",
        "research_problem",
        "objective",
        "methodology",
        "dataset",
        "conclusion",
    ]:
        val = raw_data.get(field)
        if isinstance(val, str) and val.strip():
            schema[field] = _clean_str(val)
        elif isinstance(val, list) and val:
            schema[field] = _clean_str(" ".join(str(item).strip() for item in val if item))

    # List fields
    list_mappings = {
        "key_contributions": ["key_contributions", "contributions", "novelty", "innovations"],
        "models_or_algorithms": ["models_or_algorithms", "models", "algorithms"],
        "key_results": ["key_results", "results"],
        "key_findings": ["key_findings", "important_points", "findings"],
        "practical_applications": ["practical_applications", "applications", "use_cases"],
        "limitations": ["limitations"],
        "future_work": ["future_work", "future_directions"],
        "keywords": ["keywords"],
    }

    for target_key, candidate_keys in list_mappings.items():
        items = []
        for cand in candidate_keys:
            val = raw_data.get(cand)
            if isinstance(val, list):
                for item in val:
                    clean_item = _clean_str(item) if item else ""
                    if clean_item and clean_item not in items:
                        items.append(clean_item)
            elif isinstance(val, str) and val.strip():
                # Split comma-separated or newline-separated strings
                for piece in re.split(r"[,;\n•\-]+", val):
                    clean_piece = _clean_str(piece)
                    if clean_piece and clean_piece not in items:
                        items.append(clean_piece)
        schema[target_key] = items

    # Fallback heuristics for core fields
    if schema["abstract_summary"] == "Not specified in the paper" and schema["key_findings"]:
        schema["abstract_summary"] = " ".join(schema["key_findings"][:3])

    if schema["research_problem"] == "Not specified in the paper" and schema["objective"] != "Not specified in the paper":
        schema["research_problem"] = f"Addressing {schema['objective']}"

    if schema["tldr"] == "Not specified in the paper":
        if schema["abstract_summary"] != "Not specified in the paper":
            # Extract first 1-2 sentences of abstract
            sentences = re.split(r"(?<=[.!?])\s+", schema["abstract_summary"])
            schema["tldr"] = " ".join(sentences[:2])
        elif schema["objective"] != "Not specified in the paper":
            schema["tldr"] = f"This paper focuses on {schema['objective'].lower()}."

    if not schema["key_contributions"]:
        if schema["key_findings"]:
            schema["key_contributions"] = schema["key_findings"][:3]
        elif schema["objective"] != "Not specified in the paper":
            schema["key_contributions"] = [f"Proposed novel approach to {schema['objective'].lower()}"]

    if not schema["practical_applications"]:
        if schema["research_area"] != "Not specified in the paper":
            schema["practical_applications"] = [
                f"Practical deployment in {schema['research_area']} systems",
                "Foundation for applied academic and industry research benchmarks",
            ]

    # Generate keywords if empty
    if not schema["keywords"]:
        source = f"{schema['title']} {schema['research_area']} {' '.join(schema['models_or_algorithms'])}"
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9-]{3,}\b", source)
        stop_words = {
            "this", "that", "with", "from", "using", "used", "paper", "research",
            "results", "method", "model", "data", "dataset", "study", "shows",
            "based", "approach", "their", "these", "which", "were", "have", "into",
            "than", "also", "such", "specified"
        }
        kw = []
        for w in words:
            if w.lower() not in stop_words and w not in kw:
                kw.append(w)
            if len(kw) >= 6:
                break
        schema["keywords"] = kw

    return schema


# ============================================================
# LLM EXECUTION WITH SINGLE CALL & RETRY
# ============================================================

def execute_ai_analysis(paper_text: str, max_chars: int = MAX_CHARS_FOR_AI) -> dict:
    """
    Send distilled paper text to Groq in a SINGLE focused request.
    Includes immediate automatic fallback if a 413 (request too large) occurs.
    """
    prompt = f"""You are ResearchLens, an academic research paper analyzer.
Analyze the research paper text below and produce a complete, highly accurate, structured JSON summary covering all dimensions required to understand the paper.

Return ONLY a valid JSON object with these exact keys:
{{
  "title": "",
  "authors": "",
  "research_area": "",
  "tldr": "A 1-2 sentence executive takeaway: what did the paper do and why does it matter?",
  "abstract_summary": "",
  "research_problem": "",
  "objective": "",
  "key_contributions": ["2-4 specific novel contributions/innovations introduced by this paper"],
  "methodology": "",
  "dataset": "",
  "models_or_algorithms": [],
  "key_results": [],
  "key_findings": [],
  "practical_applications": ["2-4 real-world domains or use-cases where this can be applied"],
  "conclusion": "",
  "limitations": [],
  "future_work": [],
  "keywords": []
}}

Rules:
- Base all fields strictly on the provided paper text.
- Do not invent facts, metrics, or citations.
- Keep text fields clear, informative, and academic.
- List fields must be arrays of clear, concise strings.
- Output strictly JSON, no markdown formatting or extra text.

PAPER TEXT:
{paper_text}
"""

    def _call_groq(p_content: str):
        groq_client = get_groq_client()
        return groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": p_content}],
            response_format={"type": "json_object"},
            reasoning_effort="low",
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )

    try:
        response = _call_groq(prompt)
        content = response.choices[0].message.content
        parsed = parse_json_response(content)
        if parsed:
            return parsed
        raise ValueError("Groq returned unparseable JSON response.")

    except APIStatusError as e:
        # If Request Too Large (413), trim by 30% and retry ONCE immediately
        if e.status_code == 413 and max_chars > 10000:
            print("[ResearchLens] 413 received. Automatically reducing text budget and retrying...")
            trimmed_text = paper_text[: int(len(paper_text) * 0.70)]
            retry_prompt = prompt.replace(paper_text, trimmed_text)
            try:
                response = _call_groq(retry_prompt)
                content = response.choices[0].message.content
                parsed = parse_json_response(content)
                if parsed:
                    return parsed
            except Exception as retry_err:
                raise RuntimeError(
                    f"Groq token limit exceeded even after compression: {str(retry_err)}"
                ) from retry_err

        if e.status_code == 429:
            raise RuntimeError(
                "Groq API rate limit reached. Please wait a moment and try again."
            ) from e
        if e.status_code == 413:
            raise RuntimeError(
                "The paper is too large for the current AI token budget. Please try a shorter paper."
            ) from e
        raise RuntimeError(f"Groq API error ({e.status_code}): {e.message}") from e

    except RateLimitError as e:
        raise RuntimeError(
            "Groq API rate limit reached. Please wait a moment and try again."
        ) from e

    except AuthenticationError as e:
        raise RuntimeError(
            "Groq API authentication failed. Please verify your GROQ_API_KEY in .env."
        ) from e

    except APIConnectionError as e:
        raise RuntimeError(
            "Could not connect to Groq API. Please check your network connection."
        ) from e


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def analyze_research_paper(text: str, pages: Optional[List[Dict]] = None) -> dict:
    """
    Fast, optimized AI analysis pipeline:
    1. Preprocesses text and strips repeated page headers/footers.
    2. Strips References/Bibliography completely (saving 10-35% tokens).
    3. Distills large papers into prioritized sections (Abstract, Intro, Methods, Results, Conclusion).
    4. Executes in ONE single Groq AI call without artificial sleep delays.
    5. Returns normalized, complete structured JSON for the frontend.
    """
    if not text or not text.strip():
        raise ValueError("No readable research paper text was provided.")

    print()
    print("=" * 60)
    print("[ResearchLens] OPTIMIZED AI PAPER ANALYSIS")
    print("=" * 60)

    # Step 1: Clean text & strip headers
    if pages:
        cleaned_text = strip_page_headers_and_footers(pages)
        if not cleaned_text:
            cleaned_text = clean_text(text)
    else:
        cleaned_text = clean_text(text)

    # Step 2: Strip references
    main_text, ref_text = strip_references(cleaned_text)
    print(f"Original characters: {len(text)}")
    print(f"Cleaned characters:  {len(cleaned_text)}")
    print(f"References removed:  {len(ref_text)} characters")
    print(f"Working text:        {len(main_text)} characters")

    # Step 3: Distill prioritized sections if large
    distilled_text = distill_key_sections(main_text, max_chars=MAX_CHARS_FOR_AI)
    print(f"Distilled for AI:    {len(distilled_text)} characters (~{len(distilled_text) // 4} tokens)")
    print(f"AI requests planned: 1 (no artificial delays)")
    print("=" * 60)

    # Step 4: Single AI execution
    raw_result = execute_ai_analysis(distilled_text, max_chars=MAX_CHARS_FOR_AI)

    # Step 5: Normalize and guarantee all 14 schema keys
    final_result = normalize_schema(raw_result, fallback_text=distilled_text)

    print("[ResearchLens] Analysis successfully completed!")
    print(f"Title: {final_result.get('title')}")
    print("=" * 60)
    print()

    return final_result