# deduction_engine.py

from tax_calculator import compute_tax
from copy import deepcopy

def safe_int(value, default=0):
    """Safely convert a value to int, stripping commas/₹ if needed."""
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("₹", "").strip()
            return int(cleaned) if cleaned else default
        return int(value)
    except Exception:
        return default


def get_form_val(form_data, candidates, default=0):
    """
    Accepts: form_data (dict-like), candidates: list of possible field names
    Returns first non-empty numeric-like string or default.
    """
    for key in candidates:
        if key in form_data and form_data.get(key) not in (None, ""):
            return form_data.get(key)
    return default


def compute_deductions(form_data, parsed_data):
    """
    Compute taxable income and tax liability based on user inputs + Form 16 data.
    Mutates a copy of parsed_data to include normalized deduction keys so downstream
    functions (suggestion generator, PDF) see the user-entered values.
    """

    # defensive
    parsed = deepcopy(parsed_data) if isinstance(parsed_data, dict) else {}

    regime = parsed.get("regime", "old")

    # Ensure numeric values
    gross_salary = safe_int(parsed.get("gross_salary", 0))
    standard_deduction = safe_int(parsed.get("standard_deduction", 0))

    # --- Step 1: Base taxable income (from Form16) ---
    taxable_income = gross_salary - standard_deduction

    # --- Step 2: Apply deductions (only in OLD regime) ---
    deductions = {}
    total_deductions = 0

    if regime == "old":
        # 80C – accept multiple input names (sec80c, section_80c, section80c, 80C)
        sec80c_raw = get_form_val(form_data, ["sec80c", "section_80c", "section80c", "80C", "investments80C"])
        sec80c = min(safe_int(sec80c_raw, 0), 150000)
        deductions["80C (PPF/ELSS/LIC etc.)"] = sec80c
        total_deductions += sec80c

        # 80CCD(1B) – NPS additional (accept nps_additional, nps_add, section_80ccd1b)
        nps_raw = get_form_val(form_data, ["nps_additional", "nps_add", "section_80ccd1b", "80CCD(1B)"])
        nps_add = min(safe_int(nps_raw, 0), 50000)
        deductions["80CCD(1B) (NPS Additional)"] = nps_add
        total_deductions += nps_add

        # 80D – Medical insurance
        med_self_raw = get_form_val(form_data, ["medical_self", "medInsuranceSelf", "section_80d_self", "80D_self"])
        med_self = min(safe_int(med_self_raw, 0), 25000)
        deductions["80D (Self+Family)"] = med_self
        total_deductions += med_self

        med_parents_raw = get_form_val(form_data, ["medical_parents", "medInsuranceParents", "80D_parents"])
        med_parents = min(safe_int(med_parents_raw, 0), 50000)
        deductions["80D (Parents)"] = med_parents
        total_deductions += med_parents

        # 80E – Education loan
        edu_loan_raw = get_form_val(form_data, ["education_loan", "educationLoan", "eduLoan"])
        edu_loan = max(0, safe_int(edu_loan_raw, 0))
        deductions["80E (Education Loan Interest)"] = edu_loan
        total_deductions += edu_loan

        # 80G – Donations
        donations_raw = get_form_val(form_data, ["donations", "donation", "section_80g"])
        donations = safe_int(donations_raw, 0)
        deductions["80G (Donations)"] = donations
        total_deductions += donations

        # 80TTA – Savings account interest (max 10k)
        tta_raw = get_form_val(form_data, ["savings_interest", "savingsInterest", "80TTA"])
        tta = min(safe_int(tta_raw, 0), 10000)
        deductions["80TTA (Savings Interest)"] = tta
        total_deductions += tta

        # 80EEB – EV loan interest (max 1.5L)
        eeb_raw = get_form_val(form_data, ["ev_loan_interest", "evLoanInterest", "ev_loan"])
        eeb = min(safe_int(eeb_raw, 0), 150000)
        deductions["80EEB (EV Loan Interest)"] = eeb
        total_deductions += eeb

        # Disability related deductions (input expected as percent or numeric marker)
        disability_self_raw = get_form_val(form_data, ["disability_self", "selfDisability"])
        disability_self = safe_int(disability_self_raw, 0)
        if disability_self >= 80:
            deductions["80U (Severe Disability - Self)"] = 125000
            total_deductions += 125000
        elif disability_self >= 40:
            deductions["80U (Disability - Self)"] = 75000
            total_deductions += 75000

        disability_dependent_raw = get_form_val(form_data, ["disability_dependent", "dependentDisability"])
        disability_dependent = safe_int(disability_dependent_raw, 0)
        if disability_dependent >= 80:
            deductions["80DD (Severe Disability - Dependent)"] = 125000
            total_deductions += 125000
        elif disability_dependent >= 40:
            deductions["80DD (Disability - Dependent)"] = 75000
            total_deductions += 75000

    # --- Step 3: Net taxable income ---
    net_taxable_income = max(0, taxable_income - total_deductions)

    # Before computing tax, update parsed (normalized) keys so other modules can read them
    parsed["section_80c"] = deductions.get("80C (PPF/ELSS/LIC etc.)", 0)
    parsed["section_80ccd1b"] = deductions.get("80CCD(1B) (NPS Additional)", 0)
    parsed["section_80d"] = deductions.get("80D (Self+Family)", 0) + deductions.get("80D (Parents)", 0)
    parsed["total_deductions"] = total_deductions
    parsed["net_taxable_income"] = net_taxable_income
    parsed["taxable_income"] = taxable_income

    # --- Step 4: Compute final tax ---
    # compute_tax expects parsed_data or numeric? In this project compute_tax earlier expected dict
    # but deduction_engine.compute_deductions previously called compute_tax(net_taxable_income, regime)
    # We'll instead call compute_tax with parsed so everything is consistent. If compute_tax only accepts income
    # adjust accordingly. Here I call compute_tax with merged parsed.
    final_tax = compute_tax(parsed)

    return {
        "regime": regime,
        "gross_salary": gross_salary,
        "standard_deduction": standard_deduction,
        "taxable_income": taxable_income,
        "deductions": deductions,
        "total_deductions": total_deductions,
        "net_taxable_income": net_taxable_income,
        "final_tax": final_tax,
        "parsed_data": parsed  # return normalized parsed for downstream use
    }


def compare_regimes(form_data, parsed_data):
    """
    Compare Old vs New regime tax liabilities.
    """
    old_result = compute_deductions(form_data, {**parsed_data, "regime": "old"})
    new_result = compute_deductions(form_data, {**parsed_data, "regime": "new"})

    better_regime = "old" if old_result["final_tax"]["old"]["final_tax"] < new_result["final_tax"]["old"]["final_tax"] else "new"

    return {
        "old": old_result,
        "new": new_result,
        "better": better_regime
    }
