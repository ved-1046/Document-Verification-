"""Deterministic extraction of canonical expense fields from document text."""
from datetime import datetime
import re
from typing import Optional

FIELD_NAMES = [
    "employee_name", "employee_id", "merchant_name", "expense_date",
    "currency", "total_amount", "expense_purpose", "reference_number",
]

_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
    "%d/%m/%Y", "%m/%d/%Y",
    "%d-%m-%Y", "%m-%d-%Y",
    "%d.%m.%Y", "%m.%d.%Y",
    "%d/%m/%y", "%m/%d/%y",
    "%d-%m-%y", "%m-%d-%y",
    "%d.%m.%y", "%m.%d.%y",
    "%d %B %Y", "%d %b %Y",
    "%d-%B-%Y", "%d-%b-%Y",
    "%d/%B/%Y", "%d/%b/%Y",
    "%d %B %y", "%d %b %y",
    "%d-%B-%y", "%d-%b-%y",
    "%B %d, %Y", "%b %d, %Y",
    "%B %d %Y", "%b %d %Y",
    "%B %d, %y", "%b %d, %y",
    "%B %d %y", "%b %d %y",
)

_DATE_RE = re.compile(
    r"\b(?:"
    r"\d{4}[/.-]\d{1,2}[/.-]\d{1,2}|"
    r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|"
    r"\d{1,2}[\s/.-]+[A-Za-z]{3,9}\.?[\s/.-]+(?:19|20)?\d{2}|"
    r"[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+(?:19|20)?\d{2}"
    r")\b",
    re.I
)

_CURRENCY_RE = re.compile(
    r"\b(INR|USD|EUR|GBP|CAD|AUD|JPY|SGD|AED|Rs\.?)\b|"
    r"(?:[₹$€£¥](?=\s*\d))|"
    r"(?:(?<=\d)[₹$€£¥])|"
    r"(?:(?<=\d\s)[₹$€£¥])",
    re.I
)

_CURRENCY_MAP = {
    "₹": "INR",
    "RS": "INR",
    "RS.": "INR",
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

_EXCLUDE_TOTAL_LINE_RE = re.compile(
    r"\b(?:"
    r"sub\s*total|subtotal|sub-total|"
    r"tax(?:\s*total)?|total\s*tax|vat(?:\s*total)?|gst(?:\s*total)?|cgst|sgst|igst|"
    r"discount(?:\s*total)?|total\s*discount|rebate|"
    r"tip|gratuity|"
    r"change(?:\s*due)?|cash\s*tendered|tendered|"
    r"total\s*(?:items?|qty|quantity|count)|items?\s*total"
    r")\b",
    re.I
)

_FINAL_TOTAL_LABEL_RE = re.compile(
    r"\b(?:"
    r"grand\s*total|"
    r"net\s*(?:payable|amount|due|total)|"
    r"final\s*(?:total|amount|due)|"
    r"total\s*payable|"
    r"amount\s*claimed|"
    r"total\s*amount\s*due|"
    r"amount\s*paid|"
    r"balance\s*due"
    r")\b",
    re.I
)

_STANDARD_TOTAL_LABEL_RE = re.compile(
    r"\b(?:"
    r"total\s*amount|"
    r"amount\s*due|"
    r"net\s*due|"
    r"total(?!\s*(?:items?|qty|quantity|count|tax|discount|sub))"
    r")\b",
    re.I
)

_AMOUNT_NUMERIC_RE = re.compile(
    r"(?:(?:INR|USD|EUR|GBP|CAD|AUD|JPY|SGD|AED|Rs\.?|[₹$€£¥])\s*)?"
    r"((?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:[.,]\d{1,2})?)"
    r"(?!\s*(?:%|kg|g\b|pcs|items?|qty))",
    re.I
)

GENERIC_DOC_TITLES = re.compile(
    r"\b(?:receipt|invoice|tax\s+invoice|retail\s+invoice|bill\s+of\s+supply|cash\s+memo|cash\s+receipt|"
    r"payment\s+receipt|reimbursement\s+form|expense\s+(?:reimbursement|claim|report|form)|"
    r"customer\s+copy|merchant\s+copy|original(?:\s+for\s+recipient)?|duplicate|triplicate|"
    r"synthetic|sample|test\s+receipt|demo\s+document)\b",
    re.I
)

DISCLAIMER_OR_GREETING = re.compile(
    r"\b(?:welcome|thank\s+you|thanks|visit\s+again|have\s+a\s+nice|not\s+a\s+real|generated\s+solely|"
    r"demo\s+account|declaration|terms\s+and\s+conditions)\b",
    re.I
)

FORM_OR_TABLE_HEADERS = re.compile(
    r"^(?:field|sample\s+value|employee(?:\s+(?:name|details?|id))?|submitter(?:\s+details?)?|"
    r"date|description|amount|qty|quantity|rate|price|s\.?no|serial|total|subtotal|"
    r"items?|particulars|category|business\s+purpose|declaration|claim\s+reference|expense\s+category)$",
    re.I
)

GENERIC_EXPENSE_CATEGORIES = re.compile(
    r"^(?:office\s+supplies|travel\s+expenses?|food\s+(?:&|and)\s+beverages?|stationery\s+items?|"
    r"miscellaneous(?:\s+expenses?)?|general\s+expenses?|local\s+(?:travel|conveyance))$",
    re.I
)

CONTACT_OR_ADDRESS = re.compile(
    r"\b(?:tel|phone|ph|mobile|fax|email|website|www\.|https?:|gstin|gst\s*no|cin|pan\s*no|vat\s*no|"
    r"pincode|pin\s*code|zip\s*code)\b|"
    r"\b\d{5,6}\b|"
    r"\b(?:street|road|avenue|lane|nagar|marg|floor|suite|block|sector|bldg|building|place|plaza|mall)\b",
    re.I
)


def normalize_amount(raw: str) -> str:
    """Normalize a numeric amount to two decimal places."""
    cleaned = re.sub(r"[^\d.,]", "", raw.strip())
    if not cleaned:
        return ""
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            cleaned = parts[0] + "." + parts[1]
        else:
            cleaned = cleaned.replace(",", "")
    try:
        val = float(cleaned)
        return f"{val:.2f}"
    except ValueError:
        return cleaned


def _label_value(text: str, labels: str) -> str | None:
    match = re.search(rf"(?:{labels})\s*[:#]?\s*([^\r\n]+)", text, re.I)
    return match.group(1).strip(" \t:-") if match else None


def _normalize_date(raw: str) -> str | None:
    raw = raw.strip().rstrip(".,")
    numeric = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", raw)
    if numeric:
        first, second = int(numeric.group(1)), int(numeric.group(2))
        if first <= 12 and second <= 12 and first != second:
            return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _merchant_display_name(raw: str) -> str:
    """Title-case a merchant while keeping short uppercase names as acronyms and preserving known casing."""
    raw = raw.strip().strip(" \t:-#*,")
    words = raw.split()
    processed = []
    for word in words:
        if word.isupper() and len(word) <= 3:
            processed.append(word)
        elif re.fullmatch(r"\d+[A-Za-z]+", word):
            processed.append(word[0].upper() + word[1:] if word.islower() else word)
        elif "-" in word:
            parts = word.split("-")
            processed.append("-".join(p.capitalize() for p in parts))
        elif word.isupper() and len(word) > 3:
            processed.append(word.title())
        elif any(c.isupper() for c in word[1:]):
            processed.append(word)
        else:
            processed.append(word.title())
    return " ".join(processed)


def _is_merchant_candidate(line: str) -> bool:
    cleaned = line.strip(" \t:-#*,")
    words = cleaned.split()
    if not (1 <= len(words) <= 6):
        return False
    if len(cleaned) < 2 or len(cleaned) > 50:
        return False
    if GENERIC_DOC_TITLES.search(cleaned):
        return False
    if DISCLAIMER_OR_GREETING.search(cleaned):
        return False
    if FORM_OR_TABLE_HEADERS.match(cleaned):
        return False
    if GENERIC_EXPENSE_CATEGORIES.match(cleaned):
        return False
    if CONTACT_OR_ADDRESS.search(cleaned):
        return False
    if _DATE_RE.search(cleaned):
        return False
    if not cleaned[0].isalnum():
        return False
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9&'.-]*|&", w) for w in words):
        return False
    return True


def _extract_amount_after_label(text: str) -> str | None:
    match = _AMOUNT_NUMERIC_RE.search(text)
    if match:
        amt = match.group(1)
        norm = normalize_amount(amt)
        if norm:
            try:
                val = float(norm)
                if val > 0:
                    if 1990 <= val <= 2099 and "." not in amt and "," not in amt and not re.search(r"[₹$€£¥]|(?:INR|USD|EUR|GBP)", text[:match.start() + len(match.group(0))], re.I):
                        return None
                    return norm
            except ValueError:
                pass
    return None


def _extract_total_amount(text: str) -> str | None:
    lines = text.splitlines()
    tier1_amounts: list[str] = []
    tier2_amounts: list[str] = []

    for index, line in enumerate(lines):
        if _EXCLUDE_TOTAL_LINE_RE.search(line):
            continue

        t1_match = _FINAL_TOTAL_LABEL_RE.search(line)
        t2_match = _STANDARD_TOTAL_LABEL_RE.search(line)

        if not t1_match and not t2_match:
            continue

        match = t1_match if t1_match else t2_match
        is_tier1 = bool(t1_match)

        after_text = line[match.end():]
        norm = _extract_amount_after_label(after_text)

        if not norm and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if not _EXCLUDE_TOTAL_LINE_RE.search(next_line) and not _FINAL_TOTAL_LABEL_RE.search(next_line):
                norm = _extract_amount_after_label(next_line)

        if norm:
            if is_tier1:
                tier1_amounts.append(norm)
            else:
                tier2_amounts.append(norm)

    unique_tier1 = sorted(set(tier1_amounts))
    unique_tier2 = sorted(set(tier2_amounts))

    if unique_tier1 and unique_tier2:
        combined = set(unique_tier1) | set(unique_tier2)
        if len(combined) == 1:
            return unique_tier1[0]
        return None

    if unique_tier1:
        return unique_tier1[0] if len(unique_tier1) == 1 else None

    if unique_tier2:
        return unique_tier2[0] if len(unique_tier2) == 1 else None

    value = _label_value(text, r"amount\s+claimed")
    if value:
        norm = _extract_amount_after_label(value)
        if norm:
            return norm

    return None


def extract_fields(text: str) -> dict[str, Optional[str]]:
    result: dict[str, Optional[str]] = {key: None for key in FIELD_NAMES}

    # ── Total Amount ─────────────────────────────────────────────────────────
    result["total_amount"] = _extract_total_amount(text)

    # ── Currency ─────────────────────────────────────────────────────────────
    currency = _CURRENCY_RE.search(text)
    if currency:
        symbol = currency.group(0).upper()
        result["currency"] = _CURRENCY_MAP.get(symbol, symbol)

    # ── Date ─────────────────────────────────────────────────────────────────
    labeled_date = _label_value(
        text,
        r"expense\s+date|transaction\s+date|invoice\s+date|receipt\s+date|bill\s+date|date"
    )
    labeled_date_found = False
    if labeled_date:
        date_match = _DATE_RE.search(labeled_date)
        if date_match:
            labeled_date_found = True
            result["expense_date"] = _normalize_date(date_match.group(0))
    if result["expense_date"] is None and not labeled_date_found:
        for candidate in _DATE_RE.findall(text):
            normalized = _normalize_date(candidate)
            if normalized:
                result["expense_date"] = normalized
                break

    # ── Employee Name & ID ───────────────────────────────────────────────────
    employee = _label_value(
        text,
        r"employee\s+name|claimant(?:\s+name|(?=\s*:))|"
        r"submitter(?:\s+name|(?=\s*:))|employee(?=\s*:)"
    )
    if employee and not re.match(r"(?:id|details?)\b", employee, re.I):
        result["employee_name"] = employee.strip().title()
    employee_id = _label_value(text, r"employee\s*id|emp\.?\s*id|emp\s*no")
    if employee_id:
        result["employee_id"] = employee_id.split()[0].upper()

    # ── Merchant Name ────────────────────────────────────────────────────────
    merchant = _label_value(
        text,
        r"merchant(?:\s+name)?|vendor(?:\s+name)?|supplier(?:\s+name)?|"
        r"seller(?:\s+name)?|store\s+name|shop\s+name|"
        r"restaurant|caf[eé]|biller|issued\s+by|company(?:\s+name)?"
    )
    if merchant:
        clean_merchant = re.split(r"\b(?:gstin|gst|cin|pan|phone|tel|address|st|rd|avenue)\b", merchant, flags=re.I)[0].strip(" \t:-,#")
        if clean_merchant and not re.fullmatch(r"[\d\s#\-]+", clean_merchant) and not re.match(r"^#?\d+", clean_merchant):
            result["merchant_name"] = _merchant_display_name(clean_merchant)

    if not result["merchant_name"]:
        first_lines = [line.strip() for line in text.splitlines() if line.strip()]
        provider = next((line for line in first_lines if re.search(r"\b(?:provider|hotel|airlines?|airways)\b", line, re.I)), None)
        if provider:
            result["merchant_name"] = _merchant_display_name(provider)
        else:
            candidates = []
            for line in first_lines[:4]:
                if _is_merchant_candidate(line):
                    candidates.append(line)
            if candidates:
                heading = candidates[0]
                first_index = first_lines.index(heading)
                if heading.isupper() and first_index + 1 < len(first_lines):
                    next_line = first_lines[first_index + 1]
                    if next_line.isupper() and _is_merchant_candidate(next_line):
                        heading = f"{heading} {next_line}"
                result["merchant_name"] = _merchant_display_name(heading)

    # ── Purpose ──────────────────────────────────────────────────────────────
    purpose = _label_value(text, r"business\s+purpose|expense\s+purpose|purpose\s+of\s+expense|purpose")
    if purpose and not re.match(r"(?:declaration|signature)\b", purpose, re.I):
        result["expense_purpose"] = purpose[:200]

    # ── Reference Number ─────────────────────────────────────────────────────
    ref_labels = (
        r"(?:receipt\s+)?ref(?:erence)?(?:\s*(?:no\.?|number|#|id))?|"
        r"invoice\s*(?:no\.?|number|#|id)|"
        r"bill\s*(?:no\.?|number|#|id)|"
        r"order\s*(?:no\.?|number|#|id)|"
        r"trans(?:action)?\s*(?:no\.?|number|#|id)|"
        r"txn\s*(?:no\.?|number|#|id)?|"
        r"folio\s*(?:no\.?|number|#|id)?"
    )
    reference = _label_value(text, ref_labels)
    if reference:
        clean_ref = reference.strip()
        if not re.search(r"^[₹$€£¥]|^(?:INR|USD|EUR|GBP)\b", clean_ref, re.I):
            match = re.search(r"\b[A-Za-z0-9][A-Za-z0-9\-_/]{2,35}\b", clean_ref)
            if match:
                val = match.group(0).upper()
                if not _normalize_date(val) and not (val.isdigit() and len(val) < 4):
                    result["reference_number"] = val

    return result
