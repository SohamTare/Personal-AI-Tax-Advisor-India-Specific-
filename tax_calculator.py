# tax_calculator.py

import random

def safe_get_value(data: dict, keys: list, default=0.0):
    """
    Return numeric value for first matching key variant from data.
    Handles strings with commas/currency symbol.
    """
    if not isinstance(data, dict):
        return default
    for k in keys:
        if k in data and data[k] not in (None, ""):
            val = data[k]
            try:
                if isinstance(val, str):
                    return float(val.replace(",", "").replace("₹", "").strip())
                if isinstance(val, (int, float)):
                    return float(val)
            except Exception:
                continue
    return default


def calculate_tax_old_regime(income: float) -> int:
    # (same as before) ...
    tax = 0
    if income <= 250000:
        tax = 0
    elif income <= 500000:
        tax = (income - 250000) * 0.05
    elif income <= 1000000:
        tax = (250000 * 0.05) + (income - 500000) * 0.20
    else:
        tax = (250000 * 0.05) + (500000 * 0.20) + (income - 1000000) * 0.30
    if income <= 500000:
        tax = 0
    tax = tax + (tax * 0.04)
    return round(tax)


def calculate_tax_new_regime(income: float) -> int:
    # (same as before) ...
    tax = 0
    if income <= 300000:
        tax = 0
    elif income <= 700000:
        tax = (income - 300000) * 0.05
    elif income <= 1000000:
        tax = (400000 * 0.05) + (income - 700000) * 0.10
    elif income <= 1200000:
        tax = (400000 * 0.05) + (300000 * 0.10) + (income - 1000000) * 0.15
    elif income <= 1500000:
        tax = (400000 * 0.05) + (300000 * 0.10) + (200000 * 0.15) + (income - 1200000) * 0.20
    else:
        tax = (400000 * 0.05) + (300000 * 0.10) + (200000 * 0.15) + (300000 * 0.20) + (income - 1500000) * 0.30

    if income <= 700000:
        tax = 0
    tax = tax + (tax * 0.04)
    return round(tax)


def generate_suggestions(parsed_data: dict, income: float) -> dict:
    """
    Generate dynamic tax-saving suggestions based on income and deductions.
    Uses safe_get_value() to read many key variants.
    """
    suggestions = {}

    # Section 80C – read from multiple possible keys
    claimed_80c = safe_get_value(parsed_data, ["section_80c", "sec80c", "80C", "investments80C", "section80c"], 0)
    options_80c = [
        "Invest in ELSS Mutual Funds for high returns and tax savings",
        "Open a Public Provident Fund (PPF) account for long-term growth",
        "Buy Life Insurance policies for yourself or dependents",
        "Increase EPF contribution via Voluntary PF",
        "Invest in National Savings Certificate (NSC) through the post office",
        "Open a 5-year tax-saving Fixed Deposit (FD) in a bank",
        "Consider Sukanya Samriddhi Yojana (for girl child)",
        "Pay tuition fees for your children — eligible under Section 80C",
        "Repay home loan principal — also covered under Section 80C"
    ]
    suggestions["80C (Investments)"] = {
        "claimed": int(claimed_80c),
        "limit": 150000,
        "remaining": max(0, 150000 - int(claimed_80c)),
        "options": random.sample(options_80c, min(4, len(options_80c))),
        "note": f"{random.choice(options_80c)}. You can claim up to ₹1,50,000 under Section 80C."
    }

    # NPS
    claimed_nps = safe_get_value(parsed_data, ["section_80ccd1b", "nps_additional", "80CCD(1B)"], 0)
    options_nps = [
        "Contribute more to the National Pension System (NPS)",
        "Use NPS Tier I for long-term retirement corpus building",
        "Leverage employer contributions for additional tax benefit",
        "Opt for auto-choice investment in NPS for better diversification"
    ]
    suggestions["NPS (80CCD(1B))"] = {
        "claimed": int(claimed_nps),
        "limit": 50000,
        "remaining": max(0, 50000 - int(claimed_nps)),
        "options": random.sample(options_nps, min(3, len(options_nps))),
        "note": f"{random.choice(options_nps)}. You can save an extra ₹50,000 under Section 80CCD(1B)."
    }

    # 80D
    claimed_80d = safe_get_value(parsed_data, ["section_80d", "medical_self", "medical_parents", "80D"], 0)
    options_80d = [
        "Buy or renew health insurance for yourself and family",
        "Add preventive health check-ups to claim small deductions",
        "Get health insurance for parents (extra ₹25,000–₹50,000 deduction)",
        "Ensure health policy covers pre-existing diseases for long-term savings",
        "Opt for family floater plans to maximize 80D benefits"
    ]
    suggestions["Health Insurance (80D)"] = {
        "claimed": int(claimed_80d),
        "limit": 25000,
        "remaining": max(0, 25000 - int(claimed_80d)),
        "options": random.sample(options_80d, min(3, len(options_80d))),
        "note": f"{random.choice(options_80d)}. Total deduction limit: ₹25,000 (₹50,000 for senior citizens)."
    }

    # General advice (unchanged)
    general_tips = [
        "Consider switching to the New Regime if deductions are limited.",
        "Plan tax-saving investments early in the financial year.",
        "Track your 26AS and AIS reports to avoid mismatches while filing.",
        "File ITR early to prevent late fees and last-minute stress.",
        "Review your Form 16 and Form 26AS before submission.",
        "Opt for e-verification immediately after filing to complete the process.",
        "Use the Income Tax portal’s comparison tool for regime selection."
    ]
    suggestions["General Advice"] = random.sample(general_tips, 2)

    return suggestions


def compute_tax(parsed_data: dict) -> dict:
    """
    Compute tax summary based on parsed_data dict (which should include taxable_income).
    This returns the same shape your app expects: {'old': {'final_tax': ...}, 'new': {...}, 'suggestions': {...}}
    """
    # safety
    if not isinstance(parsed_data, dict):
        parsed_data = {}

    income = safe_get_value(parsed_data, ["taxable_income", "net_taxable_income", "income", "Taxable Income"], 0.0)
    if income < 0 or not income:
        income = 0.0

    old_regime = calculate_tax_old_regime(income)
    new_regime = calculate_tax_new_regime(income)

    # ensure fallback keys are set (not required but useful)
    if "section_80c" not in parsed_data:
        parsed_data["section_80c"] = safe_get_value(parsed_data, ["80C", "sec80c", "section80c"], 0)
    if "section_80d" not in parsed_data:
        parsed_data["section_80d"] = safe_get_value(parsed_data, ["80D", "medical_self", "medical_parents"], 0)
    if "section_80ccd1b" not in parsed_data:
        parsed_data["section_80ccd1b"] = safe_get_value(parsed_data, ["80CCD(1B)", "nps_additional"], 0)

    suggestions = generate_suggestions(parsed_data, income)

    return {
        "old": {"final_tax": old_regime},
        "new": {"final_tax": new_regime},
        "suggestions": suggestions,
    }
