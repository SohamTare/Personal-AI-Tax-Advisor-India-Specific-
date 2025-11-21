import os
import sys
import traceback
import io
import re
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_from_directory, session, make_response
)
from werkzeug.utils import secure_filename

# ---- Import backend modules ----
from parser import parse_form16
from tax_calculator import compute_tax
from deduction_engine import compute_deductions, compare_regimes

# ReportLab for PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ---- Flask Setup ----
app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---- Helpers ----
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_label(key: str) -> str:
    key = key.replace("_", " ")
    return re.sub(r'(?<!^)(?=[A-Z])', " ", key).title()


def safe_float(value, default=0.0):
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        s = str(value).replace(",", "").replace("₹", "").strip()
        if s == "":
            return float(default)
        return float(s)
    except (ValueError, TypeError):
        return float(default)


def normalize_keys(data: dict) -> dict:
    """
    Convert common front-end names (various cases/styles) into backend-compatible keys.
    Keeps unknown keys as-is.
    """
    key_map = {
        # 80C
        "80c": "section_80c",
        "sec80c": "section_80c",
        "section80c": "section_80c",
        "section_80c": "section_80c",
        "investments80c": "section_80c",
        "investments80C": "section_80c",
        "investments80": "section_80c",

        # 80D
        "80d": "section_80d",
        "section80d": "section_80d",
        "medinsuranceself": "section_80d",
        "medinsuranceparents": "section_80d",
        "medinsurenceself": "section_80d",

        # 80CCD(1B)
        "80ccd1b": "section_80ccd1b",
        "section80ccd1b": "section_80ccd1b",
        "nps_additional": "section_80ccd1b",
        "npsadditional": "section_80ccd1b",
        "nps_add": "section_80ccd1b",

        # taxable income synonyms
        "taxableincome": "taxable_income",
        "taxable_income": "taxable_income",
    }

    normalized = {}
    for k, v in data.items():
        cleaned = (
            k.lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        mapped_key = key_map.get(cleaned, k)
        normalized[mapped_key] = v
    return normalized


# ======================= UPDATED FUNCTION BELOW ==========================
def generate_pdf(parsed_data, user_data, tax_summary):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=60, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    # --- Title ---
    elements.append(Paragraph("AI Tax Advisor - Tax Report", styles["Title"]))
    elements.append(Spacer(1, 20))

    # --- Personal Information ---
    elements.append(Paragraph("Personal Information", styles["Heading2"]))
    user_table_data = [["Field", "Value"]]
    for k, v in user_data.items():
        user_table_data.append([format_label(k), str(v)])
    user_table = Table(user_table_data, colWidths=[200, 280])
    user_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(user_table)
    elements.append(Spacer(1, 20))

    # --- Form 16 Extracted Data ---
    elements.append(Paragraph("Form 16 Extracted Data", styles["Heading2"]))
    form16_table_data = [["Field", "Value"]]
    for k, v in parsed_data.items():
        form16_table_data.append([format_label(k), str(v)])
    form16_table = Table(form16_table_data, colWidths=[200, 280])
    form16_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(form16_table)
    elements.append(Spacer(1, 20))

    # --- Tax Summary ---
    elements.append(Paragraph("Tax Summary", styles["Heading2"]))
    summary_table_data = [
        ["Old Regime Tax", str(tax_summary.get("old", {}).get("final_tax", "N/A"))],
        ["New Regime Tax", str(tax_summary.get("new", {}).get("final_tax", "N/A"))],
    ]
    summary_table = Table(summary_table_data, colWidths=[200, 280])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.orange),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # --- Suggestions ---
    suggestions = tax_summary.get("suggestions", {})
    if suggestions:
        elements.append(Paragraph("AI Tax Advisor Suggestions", styles["Heading2"]))
        for key, suggestion in suggestions.items():
            elements.append(Paragraph(f"<b>{format_label(key)}</b>", styles["Normal"]))
            if isinstance(suggestion, dict):
                claimed = suggestion.get("claimed")
                limit = suggestion.get("limit")
                if claimed is not None or limit is not None:
                    elements.append(Paragraph(
                        f"Claimed: {claimed}, Limit: {limit}, Remaining: {suggestion.get('remaining', '')}",
                        styles["Normal"]
                    ))
                if "note" in suggestion:
                    elements.append(Paragraph(f"Note: {suggestion['note']}", styles["Normal"]))
                if "options" in suggestion:
                    for opt in suggestion["options"]:
                        elements.append(Paragraph(f"- {opt}", styles["Normal"]))
            else:
                elements.append(Paragraph(str(suggestion), styles["Normal"]))
            elements.append(Spacer(1, 10))

    # --- DISCLAIMER ---
    disclaimer_style = styles["Normal"].clone('Disclaimer')
    disclaimer_style.fontSize = 9
    disclaimer_style.textColor = colors.black
    disclaimer_style.alignment = TA_CENTER

    disclaimer_text = """
    <b>Disclaimer:</b> This report is generated by an <b>AI-based Tax Advisor</b>.
    Please consult a qualified Chartered Accountant before making any investment or tax decision.
    """
    elements.append(Spacer(1, 18))
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    # --- Build PDF ---
    doc.build(elements)
    buffer.seek(0)
    return buffer
# ======================= UPDATED FUNCTION ENDS HERE ==========================


# ---- Routes ----
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            flash("No file uploaded.")
            return redirect(url_for("index"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.")
            return redirect(url_for("index"))

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.")
            return redirect(url_for("index"))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        parsed_data = parse_form16(filepath) or {}
        raw_user_data = {k: request.form.get(k) for k in request.form.keys()}
        normalized_user = normalize_keys(raw_user_data)
        ded_results = compute_deductions(normalized_user, parsed_data)

        session["parsed_data"] = ded_results.get("parsed_data", parsed_data)
        session["user_data"] = normalized_user
        session["tax_summary"] = ded_results.get("final_tax", {})

        return redirect(url_for("review"))

    except Exception as e:
        traceback.print_exc()
        flash(f"Processing error: {e}")
        return redirect(url_for("index"))


@app.route("/review", methods=["GET", "POST"])
def review():
    if request.method == "POST":
        updated = request.form.to_dict()
        updated = normalize_keys(updated)

        parsed = {k.replace("parsed_", ""): v for k, v in updated.items() if k.startswith("parsed_")}
        user = {k: v for k, v in updated.items() if not k.startswith("parsed_")}

        merged_parsed = session.get("parsed_data", {}).copy()
        merged_parsed.update(parsed)
        merged_user = session.get("user_data", {}).copy() if session.get("user_data") else {}
        merged_user.update(user)

        ded_results = compute_deductions(merged_user, merged_parsed)

        session["parsed_data"] = ded_results.get("parsed_data", merged_parsed)
        session["user_data"] = merged_user
        session["tax_summary"] = ded_results.get("final_tax", {})

        return redirect(url_for("result"))

    parsed_data = session.get("parsed_data")
    user_data = session.get("user_data")
    if not parsed_data:
        flash("No data available. Please upload again.")
        return redirect(url_for("index"))
    return render_template("review.html", parsed_data=parsed_data, user_data=user_data)


from suggestion_engine import generate_suggestions

@app.route("/result")
def result():
    parsed_data = session.get("parsed_data")
    user_data = session.get("user_data")
    if not parsed_data:
        flash("No analysis available. Please upload again.")
        return redirect(url_for("index"))

    merged = parsed_data.copy()
    if user_data:
        merged.update(user_data)

    merged = normalize_keys(merged)

    numeric_keys = ["taxable_income", "section_80c", "section_80ccd1b", "section_80d"]
    for nk in numeric_keys:
        if nk in merged:
            merged[nk] = safe_float(merged[nk], default=0.0)

    try:
        tax_summary = compute_tax(merged)
    except Exception as e:
        traceback.print_exc()
        flash(f"Tax calculation error: {e}")
        return redirect(url_for("review"))

    ai_suggestions = generate_suggestions()

    session["parsed_data"] = merged
    session["tax_summary"] = tax_summary

    return render_template(
        "result.html",
        parsed_data=merged,
        result=tax_summary,
        user_data=user_data,
        ai_suggestions=ai_suggestions
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/download-pdf", methods=["GET", "POST"])
def download_pdf():
    parsed_data = session.get("parsed_data", {})
    tax_summary = session.get("tax_summary", {})
    user_data = session.get("user_data", {})

    pdf_buffer = generate_pdf(parsed_data, user_data, tax_summary)
    response = make_response(pdf_buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=tax_report.pdf"
    return response


@app.route("/chapter-VIA_Deductions")
def chapter_VIA_deductions():
    return render_template("chapter-VIA_Deductions.html")


@app.route("/form-16_partA")
def form16_partA():
    return render_template("form-16_partA.html")


@app.route("/form-16_partB")
def form16_partB():
    return render_template("form-16_partB.html")


@app.route("/Gross_salary")
def gross_salary():
    return render_template("Gross_salary.html")


@app.route("/old_new-regime")
def old_new_regime():
    return render_template("old_new-regime.html")


@app.route("/TDS")
def tds():
    return render_template("TDS.html")


if __name__ == "__main__":
    app.run(debug=True)
