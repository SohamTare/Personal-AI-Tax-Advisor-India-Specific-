import re
import pdfplumber

# ---------- Small helpers ----------

def _clean_num(s: str) -> int:
    """Convert a numeric-looking string like '1,23,456' or '₹ 50,000' to int safely."""
    if s is None:
        return 0
    s = s.replace(",", "").replace("₹", "").strip()
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else 0

def _last_int_in_line(line: str) -> int:
    """Return the last integer-looking token in a line."""
    nums = re.findall(r"(\d[\d,]*)", line)
    return _clean_num(nums[-1]) if nums else 0

def _first_int_after_label_in_line(pattern: str, text: str) -> int:
    """
    Find a line matching 'pattern', then return the FIRST integer that appears
    AFTER the match. Useful when the last number isn't the right one.
    """
    pat = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        m = pat.search(line)
        if m:
            m2 = re.search(r"(\d[\d,]*)", line[m.end():])
            if m2:
                return _clean_num(m2.group(1))
    return 0

def _value_from_labeled_line(text: str, label_patterns) -> int:
    """
    Search line by line; for the first line that matches any label pattern,
    return the LAST integer on that line.
    """
    if isinstance(label_patterns, str):
        label_patterns = [label_patterns]
    compiled = [re.compile(p, re.IGNORECASE) for p in label_patterns]
    for line in text.splitlines():
        if any(p.search(line) for p in compiled):
            return _last_int_in_line(line)
    return 0

# ---------- New Regime parser ----------

def _parse_new_regime(text: str) -> dict:
    # Employee name (two-column header: Employer | Employee)
    name = "Not Found"
    m = re.search(
        r"NAME\s+AND\s+ADDRESS\s+OF\s+EMPLOYER.*?NAME\s+AND\s+ADDRESS\s+OF\s+EMPLOYEE.*?\n([^\n]+)",
        text, re.IGNORECASE
    )
    if m:
        row = m.group(1).strip()
        cols = re.split(r"\s{2,}", row)  # split columns by 2+ spaces
        if len(cols) >= 2:
            name = cols[-1].strip()

    if name == "Not Found":
        m = re.search(r"NAME\s+OF\s+EMPLOYEE\s*[:\-]?\s*([A-Z][A-Za-z .]+)", text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()

    # Assessment Year – take (AY 2025-2026) if present; else fallback to ASSESS.YEAR
    ay = "Not Found"
    m = re.search(r"\(AY\s*([0-9]{4}\s*[–-]\s*[0-9]{4})\)", text, re.IGNORECASE)
    if m:
        ay = m.group(1).replace("–", "-").replace(" ", "")
    else:
        m = re.search(r"ASSESS\.?\s*YEAR\s*[:\-]?\s*([0-9]{4}\s*[–-]\s*[0-9]{4})", text, re.IGNORECASE)
        if m:
            ay = m.group(1).replace("–", "-").replace(" ", "")

    # Line-based numeric extraction to avoid picking "(5-6)" as 5
    gross_salary = _value_from_labeled_line(text, r"\bGROSS\s+SALARY\b")
    standard_deduction = _value_from_labeled_line(text, r"Standard\s+Deduction")
    taxable_income = _value_from_labeled_line(text, r"TOTAL\s+CHARGABLE\s+INCOME")

    # Total tax payable (prefer the "in round figure" line; else use (5-6) or (3+4))
    total_tax_payable = _value_from_labeled_line(
        text,
        [r"NET\s+TAX\s+PAYABLE\s*\(in\s*round\s*figure\)", r"NET\s+TAX\s+PAYABLE\s*\(5-6\)", r"TAX\s+PAYABLE\s*\(3\+4\)"]
    )

    # TDS: prefer "TDS (9+10)"; else try other totals or sum of JAN+FEB lines
    tds_deducted = _value_from_labeled_line(text, r"TDS\s*\(9\+10\)")
    if not tds_deducted:
        # Try more general "TOTAL TAX DEDUCTED BY XYZ COMPANY" line
        tds_deducted = _value_from_labeled_line(text, r"TOTAL\s+TAX\s+DEDUCTED.*XYZ\s+COMPANY")
    if not tds_deducted:
        # Sum JAN + FEB lines if present
        jan = _value_from_labeled_line(text, r"JANUARY\s+NEXT\s+YEAR.*\(TDS\)")
        feb = _value_from_labeled_line(text, r"FEBRUARY\s+NEXT\s+YEAR.*\(TDS\)")
        tds_deducted = (jan or 0) + (feb or 0)

    refund = _value_from_labeled_line(text, r"\bREFUND\b")

    return {
        "regime": "new",
        "employee_name": name,
        "assessment_year": ay,
        "gross_salary": int(gross_salary or 0),
        "standard_deduction": int(standard_deduction or 0),
        "taxable_income": int(taxable_income or 0),
        "tds_deducted": int(tds_deducted or 0),
        "total_tax_payable": int(total_tax_payable or 0),
        "refund": int(refund or 0),
    }

# ---------- Old Regime parser ----------

def _extract_or_name(text: str) -> str:
    # Preferred: two-column "OFFICE:- <Employer>   <Employee>"
    for line in text.splitlines():
        if re.search(r"OFFICE\s*:-", line, re.IGNORECASE):
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) >= 2:
                return parts[-1].strip()

    # Next best: a line like: "   ABC   POST :- ASST. MANAGER"
    for line in text.splitlines():
        m = re.search(r"^\s*([A-Z][A-Za-z .]+)\s+POST\s*:-", line.strip())
        if m:
            return m.group(1).strip()

    # Last fallback: "NAME :- <something>" (may be employer in header)
    for line in text.splitlines():
        m = re.search(r"^NAME\s*[:-]\s*([A-Za-z .]+)$", line.strip(), re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return "Not Found"

def _extract_or_tds(text: str) -> int:
    """
    "Less Tax Deducted at Source" value may be on the next line.
    Scan a few lines starting where the label appears and pick a plausible amount.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"Less.*?Tax\s+Deducted\s+at\s+Source", line, re.IGNORECASE):
            for j in range(i, min(i + 4, len(lines))):
                nums = re.findall(r"(\d[\d,]*)", lines[j])
                # choose last plausible amount > 100
                for num in reversed(nums):
                    val = _clean_num(num)
                    if val > 100:
                        return val
    return 0

def _parse_old_regime(text: str) -> dict:
    name = _extract_or_name(text)

    # Assessment year
    ay = "Not Found"
    for line in text.splitlines():
        m = re.search(r"^ASSESSMENT\s+YEAR\s*[:-]\s*([0-9]{4}\s*[–-]\s*[0-9]{4})", line.strip(), re.IGNORECASE)
        if m:
            ay = m.group(1).replace("–", "-").replace(" ", "")
            break

    # Gross salary: "1 GROSS SALARY ... Total Rs. 1066058"
    m = re.search(r"1\s+GROSS\s+SALARY.*?Total\s+Rs\.\s*([\d,]+)", text, re.IGNORECASE | re.DOTALL)
    gross_salary = _clean_num(m.group(1)) if m else 0

    # Standard deduction: take the first number after the label on that line
    standard_deduction = _first_int_after_label_in_line(r"New\s+Standard\s+Deductions?", text)

    # Taxable income: "Income chargeable under the head salaries (3-4) Rs. 1013558"
    m = re.search(
        r"Income\s+charg[ea]ble\s+under\s+the\s+head\s+salaries.*?Rs\.\s*([\d,]+)",
        text, re.IGNORECASE | re.DOTALL
    )
    taxable_income = _clean_num(m.group(1)) if m else 0

    # TDS (Less Tax Deducted at Source)
    tds_deducted = _extract_or_tds(text)

    # Total Tax Payable
    total_tax_payable = _first_int_after_label_in_line(r"Total\s+Tax\s+Payable", text)

    # Refund: "Balance Tax Payable / Refundable (17 - 18) Rs. <val>"
    # If val < 0 => refund = -val, else refund = 0
    refund_line_val = 0
    for line in text.splitlines():
        if re.search(r"Balance\s+Tax\s+Payable\s*/\s*Refundable", line, re.IGNORECASE):
            refund_line_val = _last_int_in_line(line)
            break
    refund = max(0, -refund_line_val)

    return {
        "regime": "old",
        "employee_name": name,
        "assessment_year": ay,
        "gross_salary": int(gross_salary or 0),
        "standard_deduction": int(standard_deduction or 0),
        "taxable_income": int(taxable_income or 0),
        "tds_deducted": int(tds_deducted or 0),
        "total_tax_payable": int(total_tax_payable or 0),
        "refund": int(refund or 0),
    }

# ---------- Public API ----------

def parse_form16(pdf_path: str) -> dict:
    """
    Parse Form 16 (Old/New Regime) PDFs and return a flat dict:
    {
        "regime": "old"|"new",
        "employee_name": str,
        "assessment_year": "YYYY-YYYY",
        "gross_salary": int,
        "standard_deduction": int,
        "taxable_income": int,
        "tds_deducted": int,
        "total_tax_payable": int,
        "refund": int
    }
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])

    # Detect regime with multiple cues
    if re.search(r"FORM\s*16\s*\(AS\s*PER\s*NEW\s*REGIME\)", text, re.IGNORECASE) or \
       re.search(r"\bNEW\s+REGIME\b", text, re.IGNORECASE) or \
       "TDS (9+10)" in text:
        return _parse_new_regime(text)

    if re.search(r"\(Old\s*Tax\s*Slab\)", text, re.IGNORECASE) or \
       re.search(r"STATEMENT\s+OF\s+TAXABLE\s+INCOME", text, re.IGNORECASE):
        return _parse_old_regime(text)

    # Fallback heuristic
    return _parse_new_regime(text) if "NET TAX PAYABLE (5-6)" in text else _parse_old_regime(text)
