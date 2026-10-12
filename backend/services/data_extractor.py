import re


# ============================================================
# NUMERICAL RESULT EXTRACTION
# ============================================================

# Common research metrics.
METRIC_PATTERNS = {
    "Accuracy": r"\baccuracy\b",
    "Precision": r"\bprecision\b",
    "Recall": r"\brecall\b",
    "F1-score": r"\bf1[\s-]?score\b|\bf1\b",
    "F1": r"\bf1\b",
    "AUC": r"\bauc\b|\barea under (?:the )?curve\b",
    "Error Rate": r"\berror[\s-]?rate\b",
    "Loss": r"\bloss\b",
    "MAE": r"\bmae\b|\bmean absolute error\b",
    "MSE": r"\bmse\b|\bmean squared error\b",
    "RMSE": r"\brmse\b|\broot mean squared error\b",
    "R2": r"\br[²2]\b|\br-squared\b",
    "Runtime": r"\bruntime\b|\brun time\b",
    "Processing Time": r"\bprocessing time\b",
    "Inference Time": r"\binference time\b",
    "Training Time": r"\btraining time\b",
    "Samples": r"\bsamples?\b",
    "Dataset Size": r"\bdataset size\b",
}


# ============================================================
# VALUE PATTERN
# ============================================================

VALUE_PATTERN = re.compile(
    r"""
    (?P<value>
        \d+(?:\.\d+)?
    )
    \s*
    (?P<unit>
        %
        |percent
        |percentage
        |seconds?
        |ms
        |milliseconds?
        |minutes?
        |hours?
        |samples?
        |images?
        |records?
        |instances?
        |million
        |thousand
        |[a-zA-Z]+
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# CLEAN LABEL
# ============================================================

def clean_label(text: str):
    """
    Convert surrounding text into a useful chart label.
    """

    if not text:
        return "Overall"

    text = text.strip()

    # Remove common leading words.
    text = re.sub(
        r"^(the|a|an|our|the proposed|proposed)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove common result phrases.
    text = re.sub(
        r"\b(achieved|obtained|reported|resulted in|gave|showed|"
        r"had|with|using|of|was|is|are|reached)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s+", " ", text).strip()

    # Avoid extremely long labels.
    if len(text) > 60:
        text = text[-60:]

    if not text:
        return "Overall"

    return text


# ============================================================
# FIND NUMERICAL VALUE NEAR METRIC
# ============================================================

def extract_metric_value(line: str, metric_name: str, metric_regex: str):
    """
    Find a numerical value near a metric.
    """

    match = re.search(
        metric_regex,
        line,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    metric_start = match.start()
    metric_end = match.end()

    # Search after the metric first.
    after_metric = line[metric_end:]

    value_match = VALUE_PATTERN.search(after_metric)

    # If no value after metric, search before metric.
    if not value_match:

        before_metric = line[:metric_start]

        matches = list(
            VALUE_PATTERN.finditer(before_metric)
        )

        if matches:
            value_match = matches[-1]

            value_text = value_match.group("value")
            unit = value_match.group("unit") or ""

        else:
            return None

    else:

        value_text = value_match.group("value")
        unit = value_match.group("unit") or ""

    try:
        value = float(value_text)

        if value.is_integer():
            value = int(value)

    except ValueError:
        return None

    # Determine unit.
    unit = unit.strip()

    if unit.lower() in [
        "%",
        "percent",
        "percentage",
    ]:
        final_unit = "%"

    elif unit:
        final_unit = unit

    else:
        # Scores such as Accuracy 0.91
        final_unit = "score"

    # --------------------------------------------------------
    # Determine label
    # --------------------------------------------------------

    label_text = line[:metric_start].strip()

    # Remove punctuation.
    label_text = re.sub(
        r"^[\s:;,.\-–—]+",
        "",
        label_text,
    )

    label = clean_label(label_text)

    # If the label is too generic, use Overall.
    generic_words = [
        "",
        "overall",
        "result",
        "results",
        "performance",
        "the model",
        "model",
        "our model",
        "proposed model",
    ]

    if label.lower() in generic_words:
        label = "Overall"

    return {
        "label": label,
        "metric": metric_name,
        "value": value,
        "unit": final_unit,
    }


# ============================================================
# PROCESS ONE LINE
# ============================================================

def process_line(line: str):
    """
    Extract numerical results from one line.
    """

    results = []

    if not line.strip():
        return results

    # Ignore bibliography/reference-like lines.
    if re.match(
        r"^\s*\[\d+\]",
        line,
    ):
        return results

    for metric_name, metric_regex in METRIC_PATTERNS.items():

        result = extract_metric_value(
            line,
            metric_name,
            metric_regex,
        )

        if result:
            results.append(result)

    return results


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_results(results):
    """
    Remove duplicate numerical results.
    """

    unique = []
    seen = set()

    for result in results:

        key = (
            result["label"].lower(),
            result["metric"].lower(),
            str(result["value"]),
            result["unit"].lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(result)

    return unique


# ============================================================
# MAIN FUNCTION
# ============================================================

def extract_numerical_results(text: str):
    """
    Extract numerical research results locally.

    No Groq API call is used here.

    This makes numerical extraction:
    - very fast
    - free
    - independent of Groq rate limits
    - deterministic
    """

    if not text or not text.strip():
        return {
            "results": []
        }

    print("Starting local numerical extraction...")

    # --------------------------------------------------------
    # Normalize text
    # --------------------------------------------------------

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Split into lines.
    lines = text.split("\n")

    all_results = []

    # --------------------------------------------------------
    # Extract metrics
    # --------------------------------------------------------

    for line in lines:

        line = line.strip()

        if not line:
            continue

        line_results = process_line(line)

        if line_results:
            all_results.extend(line_results)

    # --------------------------------------------------------
    # Also check sentences.
    # --------------------------------------------------------

    # Some PDFs extract paragraphs instead of individual lines.
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    for sentence in sentences:

        if len(sentence) > 1000:
            continue

        sentence_results = process_line(sentence)

        if sentence_results:
            all_results.extend(sentence_results)

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    final_results = remove_duplicate_results(
        all_results
    )

    print(
        f"Local numerical extraction completed."
    )

    print(
        f"Found {len(final_results)} unique numerical results."
    )

    return {
        "results": final_results
    }