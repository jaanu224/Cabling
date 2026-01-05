# PDF Report Generation Guide

## Overview
The enhanced UI now generates professional PDF reports matching your template format.

## Features

### 1. Individual Reports
- **Conductor Report**: Generated after conductor calculation
- **Sheath Report**: Generated after sheath calculation (2 pages)
- Both match your exact template format with tables, equations, and conclusions

### 2. Complete Merged Report
- Combines Conductor + Sheath + Original Datasheet
- Datasheet appears at the end of the PDF
- Single comprehensive document

## How to Use

### Step 1: Upload Datasheet
1. Upload your cable datasheet PDF
2. Click "Extract From PDF"
3. System stores the datasheet for later merging

### Step 2: Calculate Conductor
1. Fill in conductor parameters (auto-filled from extraction)
2. Click "Calculate Conductor"
3. **Download button appears** - Click to get conductor report PDF

### Step 3: Calculate Sheath
1. Fill in sheath parameters
2. Click "Calculate Sheath"
3. **Download button appears** - Click to get sheath report PDF

### Step 4: Download Complete Report
1. After both calculations are done
2. **"Download Complete Report" button appears**
3. Click to get merged PDF with:
   - Conductor calculation (1 page)
   - Sheath calculation (2 pages)
   - Original datasheet (all pages)

## PDF Format

### Conductor Report Format
- Title: "SHORT CIRCUIT CURRENT CALCULATION FOR CONDUCTOR AS PER IEC 60949"
- Cable info header with yellow highlight
- Parameters table
- Equation 1 with calculations
- Conclusion

### Sheath Report Format (2 Pages)
**Page 1:**
- Title: "SHORT CIRCUIT CURRENT CALCULATION FOR THE ALUMINIUM SHEATH AS PER IEC 60949"
- Cable info and parameters
- Equation 1 (Adiabatic calculation)
- Equation 2 (Non-adiabatic)

**Page 2:**
- Equation 3 (Epsilon factor)
- Equation 4 (M factor)
- All thermal constants
- Final results
- Conclusion

## Technical Details

### Dependencies
```
Flask
pdf2image
pytesseract
reportlab
PyPDF2
```

Install with:
```bash
pip install -r enhanced_ui/requirements.txt
```

### API Endpoints
- `/api/generate_conductor_pdf` - Generate conductor report
- `/api/generate_sheath_pdf` - Generate sheath report
- `/api/generate_merged_pdf` - Generate complete merged report

### Session Storage
- Uploaded datasheet stored temporarily
- Individual reports stored for merging
- Cleaned up after merged PDF generation

## Notes
- All calculations remain identical to original
- PDF format matches your template exactly
- Original files completely untouched
- Runs on port 5001 (original on 5000)
