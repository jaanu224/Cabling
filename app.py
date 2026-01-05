import os
import re
import io

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file
)
from pdf2image import convert_from_bytes
import pytesseract

# For PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

app = Flask(__name__)

# ---------------------------------------------------------
#  CONFIG – WINDOWS PATHS (IMPORTANT)
# ---------------------------------------------------------

# Tesseract OCR executable path
TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Poppler bin path
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

# Set tesseract command explicitly
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE


# ==================== OCR HELPERS ====================

def ocr_pdf_to_text(pdf_bytes: bytes) -> str:
    pages = convert_from_bytes(
        pdf_bytes,
        dpi=300,
        poppler_path=POPPLER_PATH
    )
    text_chunks = []
    for page in pages:
        text = pytesseract.image_to_string(page, lang="eng")
        text_chunks.append(text)
    return "\n".join(text_chunks)


# ==================== TEXT PARSING HELPERS ====================

def get_first_nonempty_lines(text: str, n: int = 5):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[:n]


def extract_header_voltage_and_material(lines):
    header = " ".join(lines[:2]).lower() if lines else ""
    voltage_kv = None
    material = None

    m = re.search(r'(\d+(?:\.\d+)?)\s*k\s*?v', header)
    if m:
        voltage_kv = float(m.group(1))

    if "copper" in header or " cu " in header:
        material = "Copper"
    elif "aluminium" in header or "aluminum" in header or " al " in header:
        material = "Aluminium"

    return voltage_kv, material


def extract_header_insulation_and_outer(lines):
    header = " ".join(lines[:3]).lower() if lines else ""
    insulation = None
    outer_sheath = None

    if "xlpe" in header:
        insulation = "XLPE"
    elif "epr" in header:
        insulation = "EPR"
    elif "pvc" in header:
        insulation = "PVC"
    elif " pe " in header:
        insulation = "PE"
    elif "oil" in header:
        insulation = "Oil"

    m = re.search(r'(\b[a-z]+)\s+outer\s+sheath', header)
    if m:
        outer_sheath = m.group(1).upper()

    return insulation, outer_sheath


def extract_conductor_and_sheath_material_from_header(lines):
    header = " ".join(lines[:4]).lower() if lines else ""

    conductor = None
    sheath = None

    if re.search(r'(copper|cu).*conductor', header):
        conductor = "Copper"
    elif re.search(r'(aluminium|aluminum|al).*conductor', header):
        conductor = "Aluminium"

    if re.search(r'aluminium.*sheath', header):
        sheath = "Aluminium"
    elif re.search(r'copper.*sheath', header):
        sheath = "Copper"

    return conductor, sheath


def detect_conductor_material_global(text: str):
    t = text.lower()
    if "copper conductor" in t:
        return "Copper"
    if "aluminium conductor" in t or "aluminum conductor" in t:
        return "Aluminium"
    return None


def extract_rated_voltages(text: str):
    m = re.search(r"RATED\s+VOLTAGE\s*:\s*([0-9/\s\.]+)kV", text, re.IGNORECASE)
    if not m:
        return []
    return [float(v) for v in re.findall(r"\d+(?:\.\d+)?", m.group(1))]


def extract_short_circuit_current(text: str):
    values = re.findall(r'(\d+(?:\.\d+)?)\s*kA', text, re.IGNORECASE)
    return max(map(float, values)) if values else None


def extract_time_seconds(text: str):
    m = re.search(r'(\d+(?:\.\d+)?)\s*(s|sec|seconds)', text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def infer_k_and_beta(material: str):
    table = {
        "Copper": (226, 234.5),
        "Aluminium": (148, 228)
    }
    return table.get(material, (None, None))


def choose_main_voltage(header_voltage, rated_voltages):
    if rated_voltages:
        return max(rated_voltages)
    return header_voltage


def extract_cable_parameters(text: str):
    lines = get_first_nonempty_lines(text, n=8)

    header_voltage, header_material = extract_header_voltage_and_material(lines)
    insulation, outer_sheath = extract_header_insulation_and_outer(lines)
    conductor, sheath = extract_conductor_and_sheath_material_from_header(lines)

    conductor = conductor or detect_conductor_material_global(text) or header_material
    rated_voltages = extract_rated_voltages(text)
    scc_ka = extract_short_circuit_current(text)
    time_sec = extract_time_seconds(text)
    voltage = choose_main_voltage(header_voltage, rated_voltages)
    K, beta = infer_k_and_beta(conductor)

    return {
        "voltageKv": voltage,
        "sccKa": scc_ka,
        "timeSec": time_sec,
        "conductorMaterial": conductor,
        "sheathMaterial": sheath,
        "insulationMaterial": insulation,
        "outerSheathMaterial": outer_sheath,
        "ratedVoltages": rated_voltages,
        "kValue": K,
        "beta": beta
    }


# ==================== PDF GENERATION ====================

def build_pdf_report(title, conductor_text, sheath_text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(300, 800, title)

    c.setFont("Helvetica", 10)
    c.drawString(50, 760, conductor_text)
    c.drawString(50, 700, sheath_text)

    c.save()
    buffer.seek(0)
    return buffer


# ==================== ROUTES ====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/extract", methods=["POST"])
def api_extract():
    pdf_bytes = request.files["file"].read()
    text = ocr_pdf_to_text(pdf_bytes)
    return jsonify(extract_cable_parameters(text))


@app.route("/api/generate_pdf", methods=["POST"])
def api_generate_pdf():
    data = request.get_json()
    pdf = build_pdf_report(
        data.get("title", ""),
        data.get("conductorText", ""),
        data.get("sheathText", "")
    )
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="Cable_Report.pdf"
    )


# ==================== WINDOWS HOSTING ENTRY ====================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
