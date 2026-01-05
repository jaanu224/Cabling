// =============== BASIC DOM HANDLES ===============
const pdfInput = document.getElementById("pdfFile");
const btnExtract = document.getElementById("btnExtract");
const extractStatus = document.getElementById("extractStatus");
const rawText = document.getElementById("rawText");

const conductorForm = document.getElementById("conductorForm");
const sheathForm = document.getElementById("sheathForm");
const resultBox = document.getElementById("resultBox");
const resultText = document.getElementById("resultText");
const btnReset = document.getElementById("btnReset");

// PDF preview button
const btnViewPdf = document.getElementById("btnViewPdf");
let uploadedPdfUrl = null;

// Rated-voltage dropdown (optional)
const ratedVoltageSelect = document.getElementById("ratedVoltageSelect");
const ratedVoltageHelp = document.getElementById("ratedVoltageHelp");

// Dropdowns for insulation & outer sheath
const insulationSelect = document.getElementById("insulationMaterial");
const outerSheathSelect = document.getElementById("outerSheathMaterial");

// =============== CONSTANT TABLES ===============

// Sheaths, screens, armour (Table I)
const TABLE_I_SHEATHS = {
  lead: { K: 41, beta: 230, sigmaC: 1.45e6, rho20: 21.4e-8 },
  steel: { K: 78, beta: 202, sigmaC: 3.8e6, rho20: 13.8e-8 },
  bronze: { K: 180, beta: 313, sigmaC: 3.4e6, rho20: 3.5e-8 },
  aluminium: { K: 148, beta: 228, sigmaC: 2.5e6, rho20: 2.84e-8 }
};

// Conductors (Table I)
const TABLE_I_CONDUCTORS = {
  copper: { K: 226, beta: 234.5, sigmaC: 3.45e6, rho20: 1.7241e-8 },
  aluminium: { K: 148, beta: 228, sigmaC: 2.5e6, rho20: 2.8264e-8 }
};

// Thermal constants (ρ, σ)
const THERMAL_CONSTANTS = {
  insulating: {
    "impregnated-paper-solid": { rho: 6.0, sigma: 2.0e6 },
    "impregnated-paper-oil-filled": { rho: 5.0, sigma: 2.0e6 },
    oil: { rho: 7.0, sigma: 1.7e6 },
    PE: { rho: 3.5, sigma: 2.4e6 },
    XLPE: { rho: 3.5, sigma: 2.4e6 },
    PVC: {
      "<=3kV": { rho: 5.0, sigma: 1.7e6 },
      ">3kV": { rho: 6.0, sigma: 1.7e6 }
    },
    EPR: {
      "<=3kV": { rho: 3.5, sigma: 2.0e6 },
      ">3kV": { rho: 5.0, sigma: 2.0e6 }
    },
    "butyl-rubber": { rho: 5.0, sigma: 2.0e6 },
    "natural-rubber": { rho: 5.0, sigma: 2.0e6 }
  },
  protective: {
    "compounded-jute": { rho: 6.0, sigma: 2.0e6 },
    "rubber-sandwich": { rho: 6.0, sigma: 2.0e6 },
    polychloroprene: { rho: 5.5, sigma: 2.0e6 },
    PVC: {
      "<=35kV": { rho: 5.0, sigma: 1.7e6 },
      ">35kV": { rho: 6.0, sigma: 1.7e6 }
    },
    "PVC-bitumen": { rho: 6.0, sigma: 1.7e6 },
    PE: { rho: 3.5, sigma: 2.4e6 }
  }
};

// Thermal contact factor F
const THERMAL_CONTACT_FACTOR = {
  default: 0.7,
  "oil-filled": 1.0
};

// =============== INITIAL DEFAULTS ===============

// Default insulation = XLPE if nothing is selected
if (insulationSelect && !insulationSelect.value) {
  insulationSelect.value = "XLPE";
}

// Default outer sheath = PE if nothing is selected
if (outerSheathSelect && !outerSheathSelect.value) {
  outerSheathSelect.value = "PE";
}

// =============== UTILS ===============
function setValue(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  if (value === null || value === undefined) return;
  el.value = value;
}

function showResult(html) {
  resultText.innerHTML = html;
  resultBox.style.display = "block";

  // Auto-scroll to the Results box
  if (resultBox && typeof resultBox.scrollIntoView === "function") {
    resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function validateVoltageTime(voltageKv, t) {
  if (voltageKv <= 0 || t <= 0) {
    alert("Voltage and time must be positive.");
    return false;
  }
  if (voltageKv > 400) {
    alert("Voltage must not be greater than 400 kV.");
    return false;
  }
  if (t > 10) {
    alert("Time must not be greater than 10 seconds.");
    return false;
  }
  return true;
}

// =============== Rated Voltage dropdown helper ===============
function populateRatedVoltages(list, headerVoltage) {
  if (!ratedVoltageSelect || !ratedVoltageHelp) return;

  ratedVoltageSelect.innerHTML = "";
  if (!list || !list.length) {
    ratedVoltageSelect.style.display = "none";
    ratedVoltageHelp.style.display = "none";
    return;
  }

  ratedVoltageSelect.style.display = "block";
  ratedVoltageHelp.style.display = "block";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select rated voltage";
  ratedVoltageSelect.appendChild(placeholder);

  list.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = `${v} kV`;
    ratedVoltageSelect.appendChild(opt);
  });

  // Auto-select header voltage if it is in the list
  if (headerVoltage != null) {
    const match = list.find((v) => v === headerVoltage);
    if (match !== undefined) {
      ratedVoltageSelect.value = String(match);
    }
  }
}

if (ratedVoltageSelect) {
  ratedVoltageSelect.addEventListener("change", () => {
    const val = parseFloat(ratedVoltageSelect.value);
    if (!isNaN(val)) {
      setValue("voltageKv", val);
      setValue("sheathVoltageKv", val);
    }
  });
}

// =============== PDF PREVIEW WIRING ===============
pdfInput.addEventListener("change", () => {
  const file = pdfInput.files[0];
  if (!file) {
    uploadedPdfUrl = null;
    if (btnViewPdf) btnViewPdf.style.display = "none";
    return;
  }

  if (uploadedPdfUrl) {
    URL.revokeObjectURL(uploadedPdfUrl);
  }
  uploadedPdfUrl = URL.createObjectURL(file);

  if (btnViewPdf) {
    btnViewPdf.style.display = "inline-block";
  }
});

if (btnViewPdf) {
  btnViewPdf.addEventListener("click", () => {
    if (uploadedPdfUrl) {
      window.open(uploadedPdfUrl, "_blank");
    }
  });
}

// =============== STEP 1: PDF OCR & EXTRACTION ===============
btnExtract.addEventListener("click", async () => {
  const file = pdfInput.files[0];
  if (!file) {
    alert("Please choose a PDF file first.");
    return;
  }

  extractStatus.textContent = "Running OCR & extracting...";
  resultBox.style.display = "none";

  const fd = new FormData();
  fd.append("file", file);

  try {
    const res = await fetch("/api/extract", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Extraction failed");

    console.log("Extraction data from server:", data);

    // Choose a finalVoltage to use:
    let finalVoltage = data.voltageKv;
    if ((finalVoltage == null || isNaN(finalVoltage)) &&
        data.ratedVoltages && data.ratedVoltages.length) {
      // If header voltage missing but rated voltages exist, pick the largest (e.g. 132 or 400)
      finalVoltage = data.ratedVoltages[data.ratedVoltages.length - 1];
    }

    // Voltage / current / time
    setValue("voltageKv", finalVoltage);
    setValue("sccKa", data.sccKa);
    setValue("timeSec", data.timeSec ?? 1);

    setValue("sheathVoltageKv", finalVoltage);
    setValue("sheathSccKa", data.sccKa);
    setValue("sheathTimeSec", data.timeSec ?? 1);

    // Conductor material
    const condMat = data.conductorMaterial || data.material || "";
    if (condMat) {
      document.getElementById("material").value = condMat;
    }

    // Sheath material
    let sheathMat = data.sheathMaterial || "";
    if (!sheathMat && condMat) {
      const lower = condMat.toLowerCase();
      if (lower.includes("al")) sheathMat = "aluminium";
      else sheathMat = "aluminium"; // default
    }
    if (sheathMat) {
      const sheathSelect = document.getElementById("sheathMaterial");
      if (sheathSelect) sheathSelect.value = sheathMat;
    }

    // Insulation / outer sheath (fallback to defaults if OCR misses them)
    if (data.insulationMaterial && insulationSelect) {
      insulationSelect.value = data.insulationMaterial;
    }
    if (data.outerSheathMaterial && outerSheathSelect) {
      outerSheathSelect.value = data.outerSheathMaterial;
    }

    // K & β
    setValue("kValue", data.kValue);
    setValue("beta", data.beta);

    // Rated voltages dropdown
    populateRatedVoltages(data.ratedVoltages, data.voltageKv);

    // Debug text
    if (data.rawTextSample) rawText.textContent = data.rawTextSample;

    extractStatus.textContent =
      "Values auto-filled. Please check and edit if needed.";
  } catch (err) {
    console.error(err);
    extractStatus.textContent = "Error during extraction.";
    alert("Could not extract data from the PDF.\n\n" + err.message);
  }
});

// =============== STEP 2: CONDUCTOR CALCULATION ===============
function calculateConductorAreaFromCurrent() {
  const voltageKv = parseFloat(document.getElementById("voltageKv").value);
  const I_AD_kA = parseFloat(document.getElementById("sccKa").value);
  const t = parseFloat(document.getElementById("timeSec").value);
  const K = parseFloat(document.getElementById("kValue").value);
  const beta = parseFloat(document.getElementById("beta").value);
  const theta_i = 90;
  const theta_f = 250;

  if ([voltageKv, I_AD_kA, t, K, beta].some((v) => isNaN(v))) {
    alert("Please fill all conductor inputs.");
    return null;
  }
  if (!validateVoltageTime(voltageKv, t)) return null;
  if (I_AD_kA <= 0 || K <= 0) {
    alert("Current and K must be positive.");
    return null;
  }

  const lnTerm = Math.log((theta_f + beta) / (theta_i + beta));
  if (lnTerm <= 0) {
    alert("Invalid temperature / beta combination (ln term ≤ 0).");
    return null;
  }

  const I_AD_A = I_AD_kA * 1000;
  const S_sq = (I_AD_A ** 2 * t) / (K ** 2 * lnTerm);
  if (S_sq <= 0) {
    alert("Calculated conductor area is not valid.");
    return null;
  }

  return Math.sqrt(S_sq);
}

function calculateConductorCurrentFromArea() {
  // ⚠️ Voltage is NOT needed in this formula – removed from validation
  const t = parseFloat(document.getElementById("timeSec").value);
  const K = parseFloat(document.getElementById("kValue").value);
  const beta = parseFloat(document.getElementById("beta").value);
  const theta_i = 90;
  const theta_f = 250;
  const S_given = parseFloat(
    document.getElementById("givenConductorArea").value
  );

  if ([t, K, beta, S_given].some((v) => isNaN(v))) {
    alert(
      "For 'Calculate current using area', please fill time, K, β and given area."
    );
    return null;
  }
  if (t <= 0) {
    alert("Time must be positive.");
    return null;
  }
  if (S_given <= 0 || K <= 0) {
    alert("Area and K must be positive.");
    return null;
  }

  const lnTerm = Math.log((theta_f + beta) / (theta_i + beta));
  if (lnTerm <= 0) {
    alert("Invalid temperature / beta combination (ln term ≤ 0).");
    return null;
  }

  const I_AD_A = K * S_given * Math.sqrt(lnTerm / t);
  return I_AD_A / 1000;
}

conductorForm.addEventListener("submit", (e) => {
  e.preventDefault();
  resultBox.style.display = "none";

  const mode = document.getElementById("conductorMode").value;
  const S_given_str = document.getElementById("givenConductorArea").value;
  let html = "<b>Conductor calculation:</b><br>";

  if (mode === "area-from-current") {
    const S_required = calculateConductorAreaFromCurrent();
    if (S_required == null) return;

    html += `Required cross-sectional area S: <b>${S_required.toFixed(
      2
    )} mm²</b><br>`;

    if (S_given_str !== "") {
      const S_given = parseFloat(S_given_str);
      if (isNaN(S_given) || S_given <= 0) {
        alert("Given conductor area must be positive.");
        return;
      }
      if (S_given >= S_required) {
        html +=
          '<span style="color:green;">Cable size is sufficient for the required area.</span><br>';
      } else {
        html +=
          '<span style="color:red;">Cable undersized. Please choose the next available size.</span><br>';
      }
    }
  } else {
    const I_AD_kA = calculateConductorCurrentFromArea();
    if (I_AD_kA == null) return;
    html += `Adiabatic short-circuit current I<sub>AD</sub> for given area: <b>${I_AD_kA.toFixed(
      2
    )} kA</b><br>`;
  }

  showResult(html);
});

// =============== STEP 3: SHEATH GEOMETRY (D_outer, D_inner -> δ, area) ===============
function updateSheathGeometry() {
  const DoInput = document.getElementById("sheathOuterD");
  const DiInput = document.getElementById("sheathInnerD");
  const thicknessEl = document.getElementById("sheathThickness");
  const areaEl = document.getElementById("sheathAreaGiven");

  const Do = parseFloat(DoInput.value);
  const Di = parseFloat(DiInput.value);

  // reset borders
  DoInput.style.borderColor = "";
  DiInput.style.borderColor = "";

  if (!isNaN(Do) && !isNaN(Di) && Do > 0 && Di > 0) {
    if (Do > Di) {
      const delta = (Do - Di) / 2;
      const area = (Math.PI / 4) * (Do * Do - Di * Di);
      thicknessEl.value = delta.toFixed(3);
      areaEl.value = area.toFixed(2);
    } else {
      // outer <= inner → invalid, show red border
      thicknessEl.value = "";
      areaEl.value = "";
      DoInput.style.borderColor = "red";
      DiInput.style.borderColor = "red";
    }
  } else {
    thicknessEl.value = "";
    areaEl.value = "";
  }
}

document
  .getElementById("sheathOuterD")
  .addEventListener("input", updateSheathGeometry);
document
  .getElementById("sheathInnerD")
  .addEventListener("input", updateSheathGeometry);

// =============== SHEATH THERMAL HELPERS ===============
function getThermalConstants(materialType, materialName, voltageKv) {
  const group = THERMAL_CONSTANTS[materialType];
  if (!group) return null;
  const entry = group[materialName];
  if (!entry) return null;

  if (entry.rho !== undefined) return entry;

  if (materialType === "insulating") {
    if (materialName === "PVC" || materialName === "EPR") {
      return voltageKv <= 3 ? entry["<=3kV"] : entry[">3kV"];
    }
  } else if (materialType === "protective") {
    if (materialName === "PVC") {
      return voltageKv <= 35 ? entry["<=35kV"] : entry[">35kV"];
    }
  }
  return null;
}

function calculateM(
  insulationMaterial,
  outerSheathMaterial,
  sheathThickness,
  sheathMaterial,
  voltageKv,
  isOilFilled
) {
  const insulation = getThermalConstants(
    "insulating",
    insulationMaterial,
    voltageKv
  );
  const outerSheath = getThermalConstants(
    "protective",
    outerSheathMaterial,
    voltageKv
  );
  if (!insulation || !outerSheath) return null;

  const sigma2 = insulation.sigma;
  const rho2 = insulation.rho;
  const sigma3 = outerSheath.sigma;
  const rho3 = outerSheath.rho;

  const sheath = TABLE_I_SHEATHS[sheathMaterial];
  if (!sheath) return null;

  const sigma1 = sheath.sigmaC;
  const delta = sheathThickness;

  const F =
    isOilFilled === "yes"
      ? THERMAL_CONTACT_FACTOR["oil-filled"]
      : THERMAL_CONTACT_FACTOR.default;

  const sqrtTerm1 = Math.sqrt(sigma2 / rho2);
  const sqrtTerm2 = Math.sqrt(sigma3 / rho3);
  const numerator = sqrtTerm1 + sqrtTerm2;
  const denominator = 2 * sigma1 * delta * 1e-3;

  if (denominator === 0) return null;

  return (numerator / denominator) * F;
}

function calculateEpsilon(M, t) {
  if (M == null || isNaN(t) || t <= 0) return null;
  const MsqrtT = M * Math.sqrt(t);
  return (
    1 + 0.61 * MsqrtT - 0.069 * Math.pow(MsqrtT, 2) + 0.0043 * Math.pow(MsqrtT, 3)
  );
}

function calculateSheathAdiabaticArea(
  I_AD_kA,
  t,
  sheathMaterial,
  theta_i,
  theta_f
) {
  const mat = TABLE_I_SHEATHS[sheathMaterial];
  if (!mat) return null;

  const K = mat.K;
  const beta = mat.beta;

  const lnTerm = Math.log((theta_f + beta) / (theta_i + beta));
  if (lnTerm <= 0) return null;

  const I_AD_A = I_AD_kA * 1000;
  const s_sq = (I_AD_A ** 2 * t) / (K ** 2 * lnTerm);
  if (s_sq <= 0) return null;

  return Math.sqrt(s_sq);
}

// =============== SHEATH FORM SUBMIT ===============
sheathForm.addEventListener("submit", (e) => {
  e.preventDefault();
  resultBox.style.display = "none";

  const sheathMaterial = document
    .getElementById("sheathMaterial")
    .value.toLowerCase();
  const voltageKv = parseFloat(
    document.getElementById("sheathVoltageKv").value
  );
  const I_AD_kA = parseFloat(
    document.getElementById("sheathSccKa").value
  );
  const t = parseFloat(
    document.getElementById("sheathTimeSec").value
  );
  const insulationMaterial =
    document.getElementById("insulationMaterial").value;
  const outerSheathMaterial =
    document.getElementById("outerSheathMaterial").value;
  const theta_i = parseFloat(
    document.getElementById("sheathThetaInitial").value
  );
  const theta_f = parseFloat(
    document.getElementById("sheathThetaFinal").value
  );
  const Do = parseFloat(document.getElementById("sheathOuterD").value);
  const Di = parseFloat(document.getElementById("sheathInnerD").value);
  const sheathThickness = parseFloat(
    document.getElementById("sheathThickness").value
  );
  const s_given = parseFloat(
    document.getElementById("sheathAreaGiven").value
  );

  const isOilFilled = "no";

  if (
    !sheathMaterial ||
    [voltageKv, I_AD_kA, t, theta_i, theta_f, Do, Di, sheathThickness, s_given].some(
      (v) => isNaN(v)
    ) ||
    !insulationMaterial ||
    !outerSheathMaterial
  ) {
    alert("Please fill all sheath inputs.");
    return;
  }

  if (!validateVoltageTime(voltageKv, t)) return;
  if (I_AD_kA <= 0) {
    alert("Short-circuit current must be positive.");
    return;
  }
  if (!(Do > Di && Do > 0 && Di > 0)) {
    alert("Outer diameter must be greater than inner diameter, and both > 0.");
    return;
  }

  const s_adiab = calculateSheathAdiabaticArea(
    I_AD_kA,
    t,
    sheathMaterial,
    theta_i,
    theta_f
  );
  if (s_adiab == null) {
    alert("Could not calculate adiabatic sheath area.");
    return;
  }

  const M = calculateM(
    insulationMaterial,
    outerSheathMaterial,
    sheathThickness,
    sheathMaterial,
    voltageKv,
    isOilFilled
  );
  if (M == null) {
    alert("Could not calculate M factor (check materials / voltage).");
    return;
  }

  const epsilon = calculateEpsilon(M, t);
  if (epsilon == null) {
    alert("Could not calculate ε factor.");
    return;
  }

  const s_required = s_adiab * epsilon;

  let html = "<b>Sheath calculation:</b><br>";
  html += `Adiabatic area s<sub>adiab</sub>: <b>${s_adiab.toFixed(
    2
  )} mm²</b><br>`;
  html += `Non-adiabatic factor ε: <b>${epsilon.toFixed(
    3
  )}</b><br>`;
  html += `Required sheath area (non-adiabatic): <b>${s_required.toFixed(
    2
  )} mm²</b><br>`;
  html += `Actual sheath area from D<sub>outer</sub>, D<sub>inner</sub>: <b>${s_given.toFixed(
    2
  )} mm²</b><br>`;

  if (s_given >= s_required) {
    html +=
      '<span style="color:green;">Sheath size is sufficient for the required area.</span><br>';
  } else {
    html +=
      '<span style="color:red;">Sheath undersized. Please choose the next available size.</span><br>';
  }

  showResult(html);
});

// =============== RESET BUTTON ===============
btnReset.addEventListener("click", () => {
  window.location.reload();
});
