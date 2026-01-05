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
#  CONFIG – change these paths if your installation differs
# ---------------------------------------------------------

# Path to tesseract.exe (if not already in PATH)
TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Poppler bin path (where pdfinfo / pdftoppm / pdfimages live)
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE


# ==================== OCR HELPERS ====================

def ocr_pdf_to_text(pdf_bytes: bytes) -> str:
    """
    Convert a PDF (bytes) to text via pdf2image + Tesseract OCR.
    Handles multi-page PDFs.
    """
    pages = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=POPPLER_PATH)
    text_chunks = []
    for page in pages:
        text = pytesseract.image_to_string(page, lang="eng")
        text_chunks.append(text)
    return "\n".join(text_chunks)


# ==================== TEXT PARSING HELPERS ====================

def get_first_nonempty_lines(text: str, n: int = 5):
    """Return first n non-empty lines from OCR text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[:n]


def extract_header_voltage_and_material(lines):
    """
    Look at the first 1–2 non-empty lines for something like:
      'CROSS SECTION OF 400kV AL 1Cx2500SQmm XLPE INSULATED CABLE'
    We treat this voltage as the MAIN rated voltage (132, 220, 400, etc.).
    """
    header = " ".join(lines[:2]).lower() if lines else ""
    voltage_kv = None
    material = None

    # Voltage: e.g. '400kV', '400 kV'
    m = re.search(r'(\d+(?:\.\d+)?)\s*k\s*?v', header, flags=re.IGNORECASE)
    if m:
        try:
            voltage_kv = float(m.group(1))
        except ValueError:
            voltage_kv = None

    # Conductor material (from header only, rough)
    if "copper" in header or " cu " in header:
        material = "Copper"
    elif ("aluminium" in header or "aluminum" in header or " al " in header):
        material = "Aluminium"

    return voltage_kv, material


def extract_header_insulation_and_outer(lines):
    """
    From first few lines, detect XLPE / PE / PVC / EPR / oil,
    and outer sheath (PE, PVC, etc.).
    Example text:
      '6 segment Aluminium conductor, XLPE insulation,
       smooth Aluminium sheath and PE outer sheath...'
    """
    header = " ".join(lines[:3]).lower() if lines else ""
    insulation = None
    outer_sheath = None

    # --- Insulation material ---
    if "xlpe" in header:
        insulation = "XLPE"
    elif "epr" in header:
        insulation = "EPR"
    elif "pvc" in header:
        insulation = "PVC"
    elif ("pe insulation" in header or
          "pe insulated" in header or
          " pe " in header):
        insulation = "PE"
    elif "oil-filled" in header or "oil filled" in header:
        insulation = "oil"

    # --- Outer sheath: look for "<mat> outer sheath" ---
    m = re.search(r'(\b[a-z]+)\s+outer\s+sheath', header)
    if m:
        mat = m.group(1).upper()
        # Accept some typical outer sheath materials
        if mat in ("PE", "PVC", "XLPE", "EPR", "OIL"):
            outer_sheath = mat

    return insulation, outer_sheath


def extract_conductor_and_sheath_material_from_header(lines):
    """
    From the first few lines, try to identify:
      - conductor material  (Copper / Aluminium)
      - metallic sheath material (Aluminium / Copper / Lead / Steel / Bronze)
    Handles phrases like:
      '6 segment copper conductor, smooth aluminium sheath ...'
    """
    header = " ".join(lines[:4]).lower() if lines else ""

    conductor = None
    sheath = None

    # --- conductor material patterns ---
    if re.search(r'\b(copper|cu)\b[^,\n]*conductor', header):
        conductor = "Copper"
    elif re.search(r'\b(aluminium|aluminum|al)\b[^,\n]*conductor', header):
        conductor = "Aluminium"

    # --- sheath material patterns ---
    if re.search(r'\b(aluminium|aluminum|al)\b[^,\n]*sheath', header):
        sheath = "aluminium"
    elif re.search(r'\b(copper|cu)\b[^,\n]*sheath', header):
        sheath = "copper"
    elif re.search(r'\blead\b[^,\n]*sheath', header):
        sheath = "lead"
    elif re.search(r'\bsteel\b[^,\n]*sheath', header):
        sheath = "steel"
    elif re.search(r'\bbronze\b[^,\n]*sheath', header):
        sheath = "bronze"

    return conductor, sheath


def detect_conductor_material_global(text: str):
    """
    Aggressive scan of the WHOLE OCR text to find conductor material.
    Used as backup when header isn’t clear.
    """
    lower = text.lower()

    # Strong patterns
    if "copper conductor" in lower or "cu conductor" in lower:
        return "Copper"
    if ("aluminium conductor" in lower or
            "aluminum conductor" in lower or
            "al conductor" in lower):
        return "Aluminium"

    # Weaker heuristic
    has_copper = "copper" in lower or " cu " in lower
    has_al = ("aluminium" in lower or
              "aluminum" in lower or
              " al " in lower)

    if has_copper and not has_al:
        return "Copper"
    if has_al and not has_copper:
        return "Aluminium"

    return None


def extract_rated_voltages(text: str):
    """
    Find 'RATED VOLTAGE : 76/132/145 kV' or 'RATED VOLTAGE: 220/400/420 kV'
    and return list [76, 132, 145] or [220, 400, 420].
    """
    m = re.search(
        r"RATED\s+VOLTAGE\s*:\s*([0-9/\s\.]+)kV",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return []

    nums_str = m.group(1)
    nums = []
    for num in re.findall(r"\d+(?:\.\d+)?", nums_str):
        try:
            nums.append(float(num))
        except ValueError:
            continue
    return nums


def extract_short_circuit_current(text: str):
    """
    Aggressively try to find the short-circuit current in kA.
    We focus on lines mentioning 'short / circuit / fault / Ik / Isc'
    plus 'kA'.
    """
    lines = text.splitlines()
    candidates = []

    keywords = ("short", "circuit", "fault", "ik", "isc")

    # Pass 1: lines clearly related to short-circuit current
    for line in lines:
        lower = line.lower()
        if any(k in lower for k in keywords) and ("k" in lower and "a" in lower):
            for m in re.finditer(r'(\d+(?:[.,]\d+)?)', line):
                try:
                    val = float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
                if 0 < val < 1000:
                    candidates.append(val)

    # Pass 2: any line containing something like 'xx kA'
    if not candidates:
        for line in lines:
            lower = line.lower()
            if "k" not in lower or "a" not in lower:
                continue
            for m in re.finditer(r'(\d+(?:[.,]\d+)?)', line):
                try:
                    val = float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
                if 0 < val < 1000:
                    candidates.append(val)

    if not candidates:
        return None

    # Use the maximum candidate as the worst-case short-circuit current
    return max(candidates)


def extract_time_seconds(text: str):
    """
    Try to find short-circuit duration (e.g. '1 s', '3 sec', '3 seconds').
    Prefer lines that mention 'short / circuit / fault / Ik / Isc'.
    """
    lines = text.splitlines()
    keywords = ("short", "circuit", "fault", "ik", "isc")

    # Pass 1: relevant lines
    for line in lines:
        lower = line.lower()
        if any(k in lower for k in keywords):
            m = re.search(
                r'(\d+(?:[.,]\d+)?)\s*(s|sec|secs|second|seconds)\b',
                lower,
                re.IGNORECASE,
            )
            if m:
                try:
                    return float(m.group(1).replace(",", "."))
                except ValueError:
                    pass

    # Pass 2: anywhere in text
    m = re.search(
        r'(\d+(?:[.,]\d+)?)\s*(s|sec|secs|second|seconds)\b',
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None

    return None


def infer_k_and_beta(material: str):
    """
    For conductor only, use Table I constants.
    """
    if not material:
        return None, None

    mat_key = material.lower()
    table = {
        "copper": {"K": 226, "beta": 234.5},
        "aluminium": {"K": 148, "beta": 228},
        "aluminum": {"K": 148, "beta": 228},
    }
    row = table.get(mat_key)
    if not row:
        return None, None

    return row["K"], row["beta"]


def choose_main_voltage(header_voltage, rated_voltages):
    """
    Decide which single voltage (kV) should be used as the main system voltage.

    NEW LOGIC (matches what you want):
      1) If a RATED VOLTAGE list exists, ALWAYS choose from that list:
         - Prefer standard system values in this order:
           400, 220, 132, 66, 33, 11
         - Otherwise use the maximum value from the list.
      2) Only if there is NO rated-voltage list, fall back to header_voltage.
    """
    if rated_voltages:
        preferred = [400, 220, 132, 66, 33, 11]
        # First try to match a "standard" system voltage
        for p in preferred:
            for v in rated_voltages:
                if abs(v - p) < 1e-6:
                    return v
        # Otherwise, just take the largest
        return max(rated_voltages)

    # No rated-voltage line found → use header voltage (may be None)
    return header_voltage


def extract_cable_parameters(text: str):
    """
    Main extraction from OCR text.
    Returns a dict that frontend JS will use to auto-fill.
    """
    # Use a few top non-empty lines as "header"
    lines = get_first_nonempty_lines(text, n=8)

    header_voltage, header_material = extract_header_voltage_and_material(lines)
    insulation, outer_sheath = extract_header_insulation_and_outer(lines)
    header_conductor, sheath_material = extract_conductor_and_sheath_material_from_header(lines)

    # Conductor material:
    # 1) exact header patterns (e.g. "copper conductor")
    # 2) global scan of whole text
    # 3) fallback to generic header material
    conductor_material = (
        header_conductor
        or detect_conductor_material_global(text)
        or header_material
    )

    rated_voltages = extract_rated_voltages(text)
    scc_ka = extract_short_circuit_current(text)
    time_sec = extract_time_seconds(text)

    # Decide which single voltage we will actually use
    main_voltage = choose_main_voltage(header_voltage, rated_voltages)

    result = {
        # Main system voltage (e.g. 132, 220, 400)
        "voltageKv": main_voltage,

        # Short-circuit current and time
        "sccKa": scc_ka,
        "timeSec": time_sec,

        # Materials
        "material": conductor_material,          # for existing JS usage
        "conductorMaterial": conductor_material,
        "sheathMaterial": sheath_material,

        "insulationMaterial": insulation,        # XLPE / PE / PVC / EPR / oil (may be None)
        "outerSheathMaterial": outer_sheath,     # PE / PVC / etc. (may be None)

        # Rated voltages list from "RATED VOLTAGE: .. kV"
        "ratedVoltages": rated_voltages,
    }

    # K & beta for conductor (if we know the material)
    if conductor_material:
        K, beta = infer_k_and_beta(conductor_material)
        result["kValue"] = K
        result["beta"] = beta
    else:
        result["kValue"] = None
        result["beta"] = None

    # Send a small header snippet back for debug display
    result["rawTextSample"] = "\n".join(lines)

    return result


# ==================== PDF GENERATION HELPERS ====================

def build_pdf_report(title: str, conductor_text: str, sheath_text: str) -> io.BytesIO:
    """
    Build a simple A4 PDF with a layout suitable for your calculation report.
    You can tune fonts / positions later to match your exact template.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Margins
    left_margin = 20 * mm
    right_margin = 20 * mm
    top_margin = 25 * mm
    bottom_margin = 20 * mm

    # Title
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(
        width / 2.0,
        height - top_margin,
        title or "Cable Short Circuit Calculation"
    )

    # Small line under title
    c.setLineWidth(0.5)
    c.line(
        left_margin,
        height - top_margin - 5,
        width - right_margin,
        height - top_margin - 5
    )

    # Helper to draw a block with heading and multi-line text
    def draw_block(heading: str, block_text: str, start_y: float) -> float:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_margin, start_y, heading)
        c.setFont("Helvetica", 9)
        y = start_y - 12

        if not block_text:
            block_text = "No data."

        for line in block_text.splitlines():
            if y < bottom_margin:
                c.showPage()
                c.setFont("Helvetica", 9)
                y = height - top_margin
            c.drawString(left_margin, y, line)
            y -= 11
        return y - 10  # some extra spacing after block

    # Starting Y for body text
    text_y = height - top_margin - 20

    # Draw conductor block
    text_y = draw_block(
        "CONDUCTOR SHORT CIRCUIT CALCULATION",
        conductor_text,
        text_y
    )

    # Draw sheath block
    draw_block(
        "SHEATH SHORT CIRCUIT CALCULATION",
        sheath_text,
        text_y
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ==================== FLASK ROUTES ====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/extract", methods=["POST"])
def api_extract():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        pdf_bytes = f.read()
        text = ocr_pdf_to_text(pdf_bytes)
        data = extract_cable_parameters(text)
        return jsonify(data)
    except Exception as e:
        print("ERROR in /api/extract:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_pdf", methods=["POST"])
def api_generate_pdf():
    """
    Expects JSON:
    {
      "title": "Cable Short Circuit Calculation",
      "conductorText": "....",
      "sheathText": "...."
    }
    Returns a PDF file.
    """
    try:
        data = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body must be an object"}), 400

    title = data.get("title", "Cable Short Circuit Calculation")
    conductor_text = data.get("conductorText", "")
    sheath_text = data.get("sheathText", "")

    try:
        pdf_buffer = build_pdf_report(title, conductor_text, sheath_text)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Cable_ShortCircuit_Report.pdf",
        )
    except Exception as e:
        print("ERROR in /api/generate_pdf:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
