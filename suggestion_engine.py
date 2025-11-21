# suggestion_engine.py
import random

def generate_suggestions():
    """
    Returns randomized suggestions for deductions each time.
    """

    suggestion_pool = {
        "80C (Investments)": [
            "Invest in ELSS Mutual Funds for better long-term tax savings.",
            "Try a 5-year Tax Saving Fixed Deposit for secure returns.",
            "Buy a Life Insurance policy to save tax and protect your family.",
            "Consider Public Provident Fund (PPF) for safe and steady growth.",
            "You can also explore National Savings Certificate (NSC) via post office."
        ],
        "80CCD(1B) (NPS Additional)": [
            "Contribute extra ₹50,000 to NPS for additional tax benefits.",
            "Top-up your NPS account for better retirement planning.",
            "Don’t miss the ₹50,000 extra deduction under Section 80CCD(1B)."
        ],
        "80D (Health Insurance)": [
            "Pay health insurance premium for yourself and your parents.",
            "Opt for preventive health checkups to claim additional ₹5,000.",
            "Consider family floater insurance for wider coverage."
        ],
        "80G (Donations)": [
            "Donate to registered NGOs or PM Relief Fund to claim 50%-100% deduction.",
            "Support charitable organizations to save tax while making impact.",
        ],
        "80TTA (Savings Interest)": [
            "Earn tax-free savings interest up to ₹10,000 under 80TTA.",
            "Maintain a healthy savings account for both returns and deductions."
        ]
    }

    # Randomly select 2-3 suggestions per category
    randomized = {}
    for section, options in suggestion_pool.items():
        randomized[section] = random.sample(options, k=min(2, len(options)))

    return randomized
