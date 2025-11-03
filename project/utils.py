import os
from fpdf import FPDF
from flask import current_app

# --- Text Cleaning ---
def clean_text(text):
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '–': '-', '’': "'", '‘': "'", '“': '"', '”': '"', '…': '...'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', 'ignore').decode('latin-1')


# --- Approximate line count ---
def get_line_count_fast(text, col_width, char_width=2.5):
    if not text:
        return 1
    approx_chars_per_line = max(int(col_width / char_width), 1)
    lines = 0
    for paragraph in text.split('\n'):
        lines += max(1, (len(paragraph) - 1) // approx_chars_per_line + 1)
    return lines


# --- PDF Generation ---
def generate_report_pdf(report, results):
    """Generates PDF report and returns bytes."""

    # Precompute image paths (check existence once)
    logo_path = os.path.join(current_app.static_folder, 'heritage-logo.png')
    purity_path = os.path.join(current_app.static_folder, 'purity-logo.png')
    if not os.path.exists(logo_path):
        logo_path = None
    if not os.path.exists(purity_path):
        purity_path = None

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(255, 255, 255)
            self.rect(0, 0, 210, 30, 'F')
            self.set_text_color(0, 0, 0)
            if logo_path:
                self.image(logo_path, x=10, y=8, w=35)
            if purity_path:
                self.image(purity_path, x=150, y=8, w=45)
            self.ln(25)

    pdf = PDF('P', 'mm', 'A4')
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=15)

    # --- Report Header ---
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, clean_text('BATCH WISE – TEST REPORT'), ln=True, align='C')
    pdf.set_line_width(0.5)
    pdf.line(75, pdf.get_y(), 135, pdf.get_y())
    pdf.ln(5)

    pdf.set_font('helvetica', '', 9)
    intro_text = (
        "Each batch of milk is rigorously tested to ensure purity, safety, and nutrition. "
        "From arrival to dispatch, it’s screened for key quality markers like fat, protein, "
        "microbial safety & adulterants. With advanced technology and expert care, only milk "
        "that meets the highest standards reaches your home."
    )
    pdf.multi_cell(0, 4, clean_text(intro_text), align='C')
    pdf.ln(5)

    # --- Product Details ---
    pdf.set_fill_color(255, 235, 59)
    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(47.5, 7, '', border=1)
    pdf.cell(142.5, 7, 'Heritage Foods Limited QA Department', ln=True, align='C', fill=True, border=1)

    pdf.cell(47.5, 7, '', border='L,R,B')
    pdf.cell(71.25, 7, 'Unit:', 1, 0, 'C', 1)
    pdf.set_font('helvetica', '', 11)
    pdf.cell(71.25, 7, clean_text(report.plant_name), 1, 1, 'C', 1)

    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(47.5, 7, 'Product Name', 1, 0, 'C')
    pdf.set_font('helvetica', '', 9)
    pdf.cell(142.5, 7, clean_text(report.product.name), 1, 1, 'C')

    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(47.5, 7, 'Batch No.', 1, 0, 'C')
    pdf.set_font('helvetica', '', 9)
    pdf.cell(47.5, 7, clean_text(report.batch_code), 1, 0, 'C')
    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(47.5, 7, 'Use by date', 1, 0, 'C')
    pdf.set_font('helvetica', '', 9)
    pdf.cell(47.5, 7, report.expiry_date.strftime('%d.%m.%Y'), 1, 1, 'C')

    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 7, 'Certificate of Analysis', ln=True, align='C', fill=True, border=1)
    pdf.ln(0.1)

    # --- Results Table ---
    line_height = 5
    col_w = {'sno': 15, 'param': 55, 'spec': 50, 'result': 30}
    col_w['method'] = 190 - sum(col_w.values())

    # Table Header
    pdf.set_font('helvetica', 'B', 9)
    for key, header in zip(['sno','param','spec','result','method'], ['S.No','Parameters','Specifications','Results','Methods /reference']):
        pdf.cell(col_w[key], 6, header, 1, 0 if key != 'method' else 1, 'C')

    # Table Rows
    pdf.set_font('helvetica', '', 8)
    for i, r in enumerate(results, 1):
        row_height = max(
            get_line_count_fast(str(i), col_w['sno']),
            get_line_count_fast(r.template.parameter, col_w['param']),
            get_line_count_fast(r.template.specification, col_w['spec']),
            get_line_count_fast(r.result_value, col_w['result']),
            get_line_count_fast(r.template.method, col_w['method'])
        ) * line_height

        y_start = pdf.get_y()
        x_start = pdf.get_x()

        # Draw cells
        pdf.multi_cell(col_w['sno'], line_height, str(i), 1, 'C')
        pdf.set_xy(x_start + col_w['sno'], y_start)
        pdf.multi_cell(col_w['param'], line_height, r.template.parameter, 1)
        pdf.set_xy(x_start + col_w['sno'] + col_w['param'], y_start)
        pdf.multi_cell(col_w['spec'], line_height, r.template.specification, 1)
        pdf.set_xy(x_start + col_w['sno'] + col_w['param'] + col_w['spec'], y_start)
        pdf.multi_cell(col_w['result'], line_height, r.result_value, 1, 'C')
        pdf.set_xy(x_start + col_w['sno'] + col_w['param'] + col_w['spec'] + col_w['result'], y_start)
        pdf.multi_cell(col_w['method'], line_height, r.template.method, 1)
        pdf.set_y(y_start + row_height)

    # --- Signature ---
    if report.creator and report.creator.signature_filename:
        sig_path = os.path.join(current_app.config['UPLOAD_FOLDER'], report.creator.signature_filename)
        if os.path.exists(sig_path):
            pdf.image(sig_path, x=150, y=pdf.get_y() + 5, w=35)

    pdf.set_font('helvetica', '', 10)
    pdf.set_y(pdf.get_y() + 20)
    pdf.set_x(150)
    pdf.cell(40, 5, 'Plant QA Incharge', ln=True, align='C')

    return pdf.output(dest='S').encode('latin1')
