"""
File parser -- handles Excel, CSV, and PDF inputs.
Robust against messy real-world files: merged cells, multi-header rows,
blank rows, mixed types, bad encoding, unnamed columns, huge files.
Returns a structured dict that agents can query.
"""
import io
import re
import pandas as pd
import pdfplumber
from pathlib import Path


# Max rows sent to agents per sheet (keeps context window manageable)
MAX_SAMPLE_ROWS = 60
# Max sheets processed per workbook
MAX_SHEETS = 20
# Max PDF pages
MAX_PDF_PAGES = 30
MAX_CONTENT_BYTES = 25 * 1024 * 1024   # 25 MB — financial docs are small; bounds memory/time on pathological uploads
_MAX_CELL_CHARS = 2000                 # truncate absurdly long individual cell values (prompt-bloat + DoS guard)


def parse_file(filename: str, content: bytes) -> dict:
    """
    Route to the correct parser based on file extension.
    Returns a dict with domain-keyed sections. Total: never raises on bad input.
    """
    filename = filename or "upload"
    if content is None:
        return {"general": {"filename": filename, "error": "no content"}}
    if len(content) > MAX_CONTENT_BYTES:
        return {"general": {"filename": filename,
                            "error": "file too large ({:.0f} MB; max {:.0f} MB)".format(
                                len(content) / 1e6, MAX_CONTENT_BYTES / 1e6)}}
    ext = Path(filename).suffix.lower()
    if ext in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        return _parse_excel(filename, content)
    elif ext in (".csv", ".tsv"):
        return _parse_csv(filename, content)
    elif ext == ".pdf":
        return _parse_pdf(filename, content)
    elif ext in (".txt", ".json"):
        return _parse_text(filename, content)
    else:
        return {
            "general": {
                "filename": filename,
                "raw_text": content.decode("utf-8", errors="ignore")[:5000],
            }
        }


# ── Excel ──────────────────────────────────────────────────────────

def _parse_excel(filename: str, content: bytes) -> dict:
    result = {
        "general": {"filename": filename},
        "financial": {},
        "sheets": {},
        "_meta": {"source_file": filename, "type": "excel"},
    }
    try:
        xf = pd.ExcelFile(io.BytesIO(content))
        sheet_names = xf.sheet_names[:MAX_SHEETS]

        for sheet in sheet_names:
            try:
                df = _read_sheet_robust(xf, sheet)
                if df is None or df.empty:
                    continue
                sheet_data = _df_to_summary(df, sheet_name=sheet)
                result["sheets"][sheet] = sheet_data

                # Route by sheet name keywords
                sn = sheet.lower()
                domain = _detect_domain(sn)
                if domain == "financial":
                    result["financial"][sheet] = sheet_data
                elif domain:
                    result.setdefault(domain, {})[sheet] = sheet_data
                else:
                    result["general"][sheet] = sheet_data

            except Exception as sheet_err:
                result["sheets"][sheet] = {"error": str(sheet_err)}

    except Exception as e:
        result["error"] = f"Excel parse failed: {e}"
    # Aggregate clean per-sheet text so downstream consumers get readable lines
    _parts = []
    for _name, _sd in result.get("sheets", {}).items():
        if isinstance(_sd, dict) and _sd.get("text"):
            _parts.append("[{}]\n{}".format(_name, _sd["text"]))
    result["text"] = "\n\n".join(_parts)
    return result


def _read_sheet_robust(xf: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """
    Read a sheet with fallbacks for common real-world problems:
    - Merged/blank header rows
    - Leading empty rows
    - Mixed data types in columns
    - Unnamed columns (Unnamed: 0, 1, ...)
    """
    # First attempt: normal read
    try:
        df = pd.read_excel(xf, sheet_name=sheet, header=0)
    except Exception:
        df = pd.read_excel(xf, sheet_name=sheet, header=None)

    # Drop completely empty rows and columns
    df = df.dropna(how="all").reset_index(drop=True)
    df = df.dropna(axis=1, how="all")

    if df.empty:
        return None

    # If the first row looks like a title/report name (1-2 non-null values),
    # try reading with header on row 1 instead
    first_row_filled = df.iloc[0].notna().sum()
    total_cols = len(df.columns)
    if total_cols > 3 and first_row_filled <= 2:
        try:
            df2 = pd.read_excel(xf, sheet_name=sheet, header=1)
            df2 = df2.dropna(how="all").reset_index(drop=True)
            df2 = df2.dropna(axis=1, how="all")
            if not df2.empty and len(df2) > 1:
                df = df2
        except Exception:
            pass

    # Clean up column names
    df.columns = _clean_column_names(df.columns)

    # Convert columns to best inferred types
    df = _coerce_types(df)

    return df


def _clean_column_names(columns) -> list:
    """Normalise column names: strip whitespace, replace unnamed, deduplicate."""
    seen = {}
    clean = []
    for i, col in enumerate(columns):
        name = str(col).strip()
        # Drop pandas default "Unnamed: N" columns where N is a number
        if re.match(r"^Unnamed:\s*\d+", name) or name in ("nan", "None", ""):
            name = f"col_{i}"
        # Deduplicate
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        clean.append(name)
    return clean


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Try to parse columns that look numeric but came in as object."""
    for col in df.select_dtypes(include="object").columns:
        # Try numeric
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() / max(len(df), 1) > 0.6:
            df[col] = converted
            continue
        # Try date — but skip columns whose values are too long to be a date. No real
        # date is >40 chars, and dateutil's fallback is pathologically slow on huge
        # strings, so one giant cell could otherwise hang the whole parse (DoS guard).
        try:
            _maxlen = df[col].astype(str).str.len().max()
            if pd.notna(_maxlen) and _maxlen > 40:
                continue
            date_converted = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if date_converted.notna().sum() / max(len(df), 1) > 0.6:
                df[col] = date_converted.dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return df


def _detect_domain(sheet_name_lower: str) -> str:
    """Map a sheet name to a domain bucket."""
    mapping = {
        "financial": ["financ", "p&l", "income", "revenue", "profit", "loss",
                      "expense", "budget", "cash", "balance", "trial", "ledger",
                      "gl ", "general ledger", "vat", "tax"],
        "hr":        ["payroll", "hr", "staff", "employee", "salary", "wage",
                      "leave", "headcount", "personnel", "labour", "labor"],
        "sales":     ["sales", "order", "customer", "crm", "invoice", "quote",
                      "pipeline", "deal", "revenue_by", "client"],
        "logistics": ["fleet", "vehicle", "fuel", "logistics", "route", "driver",
                      "trip", "delivery", "dispatch", "truck", "freight"],
        "procurement": ["stock", "inventory", "supplier", "purchase", "procurement",
                        "bom", "material", "warehouse", "store"],
        "marketing": ["market", "campaign", "lead", "advertising", "social",
                      "digital", "seo", "email", "ads", "spend"],
        "accounting": ["debtors", "creditors", "accounts receivable", "accounts payable",
                       "ar ", "ap ", "aging", "overdue"],
    }
    for domain, keywords in mapping.items():
        if any(k in sheet_name_lower for k in keywords):
            return domain
    return ""


# ── CSV ────────────────────────────────────────────────────────────

def _parse_csv(filename: str, content: bytes) -> dict:
    """Parse CSV/TSV with encoding fallback and separator detection."""
    sep = "\t" if filename.lower().endswith(".tsv") else ","

    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(
                io.BytesIO(content),
                sep=sep,
                encoding=encoding,
                on_bad_lines="skip",
                low_memory=False,
            )
            df = df.dropna(how="all").reset_index(drop=True)
            df = df.dropna(axis=1, how="all")
            df.columns = _clean_column_names(df.columns)
            df = _coerce_types(df)

            summary = _df_to_summary(df, sheet_name="csv")
            domain = _detect_domain(Path(filename).stem.lower())

            result = {
                "general": {"filename": filename},
                "financial": summary,
                "text": summary.get("text", ""),
                "_meta": {"source_file": filename, "type": "csv"},
            }
            if domain:
                result[domain] = {"data": summary}
            return result

        except Exception:
            continue

    return {"error": f"Could not parse CSV: {filename}", "general": {}}


# ── PDF ────────────────────────────────────────────────────────────

def _parse_pdf(filename: str, content: bytes) -> dict:
    result = {
        "general": {"filename": filename},
        "financial": {},
        "raw_pages": [],
        "_meta": {"source_file": filename, "type": "pdf"},
    }
    full_text = ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for i, page in enumerate(pdf.pages[:MAX_PDF_PAGES]):
                text = page.extract_text() or ""
                full_text += text + "\n"
                result["raw_pages"].append({"page": i + 1, "text": text[:1500]})

                # Extract tables
                for t_idx, table in enumerate(page.extract_tables() or []):
                    if not table or len(table) < 2:
                        continue
                    try:
                        # Use first non-empty row as header
                        header_row = 0
                        for r, row in enumerate(table):
                            if any(c for c in row if c):
                                header_row = r
                                break
                        headers = [str(c or f"col_{j}").strip()
                                   for j, c in enumerate(table[header_row])]
                        rows = table[header_row + 1:]
                        df = pd.DataFrame(rows, columns=headers)
                        df = df.dropna(how="all")
                        df.columns = _clean_column_names(df.columns)
                        df = _coerce_types(df)
                        key = f"page_{i+1}_table_{t_idx}"
                        result["financial"][key] = _df_to_summary(df, sheet_name=key)
                    except Exception:
                        pass

        result["general"]["full_text"] = full_text[:8000]
        result["financial"]["text_extract"] = full_text[:5000]
        result["text"] = full_text[:8000]

    except Exception as e:
        result["error"] = f"PDF parse failed: {e}"
    return result


# ── Plain text / JSON ──────────────────────────────────────────────

def _parse_text(filename: str, content: bytes) -> dict:
    for enc in ("utf-8", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except Exception:
            text = ""
    return {
        "general": {"filename": filename, "raw_text": text[:8000]},
        "text": text[:8000],
        "_meta": {"source_file": filename, "type": "text"},
    }


# ── Summary builder ────────────────────────────────────────────────

def _cap(x):
    """Stringify non-primitive cells and truncate absurdly long values (prompt-bloat guard)."""
    if not isinstance(x, (int, float, str, bool)):
        x = str(x)
    if isinstance(x, str) and len(x) > _MAX_CELL_CHARS:
        return x[:_MAX_CELL_CHARS] + "\u2026(truncated)"
    return x


def _df_to_summary(df: pd.DataFrame, sheet_name: str = "") -> dict:
    """Convert a DataFrame to a compact JSON-serializable summary for agents."""
    sample = df.head(MAX_SAMPLE_ROWS)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_summary = {}
    for col in numeric_cols:
        col_data = df[col].dropna()
        if len(col_data) == 0:
            continue
        numeric_summary[col] = {
            "sum": _safe_float(col_data.sum()),
            "mean": _safe_float(col_data.mean()),
            "min": _safe_float(col_data.min()),
            "max": _safe_float(col_data.max()),
            "count": int(col_data.count()),
        }

    # Safe serialisation of sample rows
    try:
        records = (
            sample
            .fillna("")
            .map(_cap)   # DataFrame.map = non-deprecated applymap (pandas>=2.1; pinned >=2.2.2)
            .to_dict(orient="records")
        )
    except Exception:
        records = []

    return {
        "sheet_name": sheet_name,
        "columns": list(df.columns),
        "row_count": len(df),
        "sample_rows": records,
        "numeric_summary": numeric_summary,
        "text": _df_to_text(df),
    }


def _df_to_text(df, max_rows: int = MAX_SAMPLE_ROWS) -> str:
    """Render a DataFrame as clean, human/LLM-readable lines.

    Critical for financial statements: a label/value sheet renders as
    'Revenue: 8000000' (one fact per line), instead of an opaque dict repr.
    This is what every agent AND the deterministic ratio extractor read, so a
    clean rendering both unblocks ratio extraction and reduces LLM hallucination.
    """
    if df is None or getattr(df, "empty", True):
        return ""
    cols = list(df.columns)
    out = []
    # Include a header line only when the columns are meaningful (not auto-named)
    meaningful = [c for c in cols if c is not None
                  and not str(c).startswith(("col_", "Unnamed"))]
    if len(cols) > 1 and len(meaningful) == len(cols):
        out.append(" | ".join(str(c) for c in cols))
    for _, row in df.head(max_rows).iterrows():
        cells = []
        for c in cols:
            v = row[c]
            try:
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    continue
            except Exception:
                pass
            sv = str(v).strip()[:_MAX_CELL_CHARS]
            if sv and sv.lower() != "nan":
                cells.append(sv)
        if not cells:
            continue
        if len(cells) == 1:
            out.append(cells[0])
        elif len(cells) == 2:
            out.append("{}: {}".format(cells[0], cells[1]))
        else:
            out.append(" | ".join(cells))
    return "\n".join(out)


def _safe_float(val) -> float:
    """Convert to float safely, returning 0.0 on failure."""
    try:
        f = float(val)
        if f != f:  # NaN check
            return 0.0
        return round(f, 4)
    except Exception:
        return 0.0


# ── Merge ─────────────────────────────────────────────────────────

def merge_parsed_data(files: list) -> dict:
    """Merge multiple file parse results into one business data dict."""
    merged = {}
    for file_data in files:
        if not isinstance(file_data, dict):   # skip None / non-dict entries defensively
            continue
        for key, value in file_data.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(merged[key], dict) and isinstance(value, dict):
                # Deep merge dicts instead of overwriting
                _deep_merge(merged[key], value)
            elif isinstance(merged[key], list) and isinstance(value, list):
                merged[key].extend(value)
    return merged


def _deep_merge(base: dict, overlay: dict):
    """In-place deep merge of overlay into base."""
    for k, v in overlay.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
