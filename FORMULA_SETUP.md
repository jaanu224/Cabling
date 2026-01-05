# Formula Image Setup Guide

## Quick Fix Applied
I've fixed the overlapping text and spacing issues in the sheath PDF.

## For Pixel-Perfect Formulas (Optional Enhancement)

To use your exact formula images:

### Step 1: Save Formula Images
Save these 3 formula screenshots as PNG files in `enhanced_ui/static/formulas/`:
- `eq2.png` - I = ε × IAD
- `eq3.png` - ε = 1 + 0.61M√t - 0.069(M√t)² + 0.0043(M√t)³  
- `eq4.png` - M = (√(σ₂/ρ₂) + √(σ₃/ρ₃)) / (2σ₁δ × 10⁻³) F

### Step 2: Create the folder
```bash
mkdir enhanced_ui\static\formulas
```

### Step 3: I'll update the code
Once you save the images, let me know and I'll update the PDF generation to use them instead of text-based formulas.

## Current Status
✅ Fixed overlapping text
✅ Fixed spacing issues  
✅ Proper alignment
⏳ Image-based formulas (waiting for PNG files)
