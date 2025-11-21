# Personal AI Tax Advisor (India Specific)
A Flask-based web app that extracts salary and tax details from Form 16 PDFs, computes tax under old vs new regimes (India), compares both, and generates dynamic AI-style tax-saving suggestions with a downloadable PDF report.

# AI Tax Advisor (India) – Form 16 Analyzer

An AI-assisted **personal tax advisor** web app (India-specific) built with **Flask**.

Upload your **Form 16 (PDF)**, review extracted data, enter your deductions (80C, 80D, NPS, etc.), and get:

- Tax calculation under **Old** and **New** regime  
- **Regime comparison** & tax savings  
- Dynamic **AI-style tax-saving suggestions**  
- Downloadable **PDF tax report** with disclaimer  

> ⚠️ **Disclaimer**  
> This tool is for **educational / helper** use only.  
> Always consult a qualified **Chartered Accountant** before making investment or tax decisions.

---

## ✨ Features

- 📄 **Form 16 PDF upload**
  - Extracts key salary / TDS / tax info using a custom parser.
- 🧮 **Tax computation**
  - Calculates tax under **Old Regime** and **New Regime** (AY 2024–25 style slabs).
  - Includes rebate u/s 87A and 4% Health & Education Cess.
- 💸 **Deductions engine**
  - Handles common sections:
    - **80C** (PPF, ELSS, LIC, EPF, tuition fees, etc.)
    - **80CCD(1B)** (NPS additional)
    - **80D** (health insurance – self, family, parents)
    - 80E, 80G, 80TTA, 80EEB, disability-related sections, etc. (for old regime)
  - Normalizes different input names (`80C`, `sec80c`, `section_80c`, etc.).
- 🤖 **AI Tax Suggestions**
  - Randomized, practical tips on:
    - 80C investments  
    - NPS (80CCD(1B))  
    - Health insurance (80D)  
    - General filing & planning tips  
  - Suggestions **refresh each time** you load the result page.
- 📊 **Dashboard-style result page**
  - Side-by-side Old vs New regime comparison.
  - Shows **which regime is better** and approximate tax saved.
- 📥 **Downloadable PDF Report**
  - Includes:
    - Personal info (from the form)
    - Form 16 extracted values
    - Tax summary
    - Suggestions
    - A clear **disclaimer** at the end.
- 🌐 **No database required**
  - Uses **Flask session** to keep data between steps (upload → review → result).

---

## 🗂 Project Structure

Typical repo structure:

```text
.
├─ app.py
├─ parser.py
├─ tax_calculator.py
├─ deduction_engine.py
├─ suggestion_engine.py        # if separated, else suggestion logic is in tax_calculator
├─ requirements.txt
├─ templates/
│  ├─ index.html
│  ├─ review.html
│  ├─ result.html
│  ├─ chapter-VIA_Deductions.html
│  ├─ form-16_partA.html
│  ├─ form-16_partB.html
│  ├─ Gross_salary.html
│  └─ TDS.html
├─ static/
│  ├─ style.css                # optional extra styling
│  └─ any images / JS
└─ uploads/                    # runtime folder for uploaded PDFs (created on server)
