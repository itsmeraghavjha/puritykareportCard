# project/routes.py
# Contains all application routes, organized by blueprints.

import os
from flask import (Blueprint, render_template, request, redirect, url_for, 
                   flash, current_app, make_response, send_from_directory, jsonify)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, date
from functools import wraps

from . import db
from .models import Product, QualityReport, ReportTemplate, User, Plant, ReportResult
from .data import AWARENESS_DATA
from .utils import generate_report_pdf

# MODIFICATION: Import the necessary tools from xhtml2pdf and io
from xhtml2pdf import pisa
from io import BytesIO

bp = Blueprint('main', __name__)




# --- Custom Decorators ---
def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'superadmin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Public Routes (Consumer Facing) ---
# @bp.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         expiry_date_str = request.form.get('expiry-date')
#         sku = request.form.get('sku')
#         batch_code = request.form.get('batch-code', '').upper()
        
#         try:
#             expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
#             if expiry_date < date.today():
#                 error = "Use by date cannot be in the past. Please select a future date."
#                 return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, error=error, now=date.today())
#             product = Product.query.filter_by(sku=sku).first()
#             if product:
#                 report = QualityReport.query.filter_by(
#                     product_id=product.id,
#                     expiry_date=expiry_date,
#                     batch_code=batch_code
#                 ).first()

#                 if report:
#                     ordered_results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
#                     return render_template('public/report.html', report=report, results=ordered_results)
#         except (ValueError, TypeError):
#             pass

#         error = "No report found. Please check the details and try again."
#         return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, now=date.today(), error=error)
        
#     return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, now=date.today())


# project/routes.py

# ... (imports and other code)

# project/routes.py

# ... (other imports)
from datetime import date # This import can be removed if not used elsewhere in the file

# ...

# @bp.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         # "expiry-date" is no longer read from the form
#         sku = request.form.get('sku')
#         batch_code = request.form.get('batch-code', '').upper()

#         product = Product.query.filter_by(sku=sku).first()
#         if product:
#             # The database query now ONLY uses product_id and batch_code
#             report = QualityReport.query.filter_by(
#                 product_id=product.id,
#                 batch_code=batch_code
#             ).first()

#             if report:
#                 ordered_results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
#                 return render_template('public/report.html', report=report, results=ordered_results)

#         error = "No report found. Please check the details and try again."
#         # The 'now' variable is no longer passed to the template
#         return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, error=error)

#     # The 'now' variable is no longer passed to the template
#     return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA)

# ... (rest of the file)



# @bp.route('/download/<int:report_id>')
# def download_pdf_report(report_id):
#     report = QualityReport.query.get_or_404(report_id)
#     results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
#     pdf_output = generate_report_pdf(report, results)
    
#     response = make_response(pdf_output)
#     response.headers['Content-Type'] = 'application/pdf'
#     response.headers['Content-Disposition'] = f'inline; filename=quality_report_{report.batch_code}.pdf'
#     return response

# @bp.route('/uploads/<path:filename>')
# def uploaded_file(filename):
#     return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# The corrected download_pdf_report function in routes.py



# BEST PRACTICE: Replace the entire 'index' function with this robust version.
@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        sku = request.form.get('sku')
        full_batch_code = request.form.get('batch-code', '').strip()

        # Centralized input validation
        if not sku or len(full_batch_code) < 5:
            error = "Please select a product and enter a valid Batch Code (at least 6 characters)."
            return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, error=error)

        # Clean, predictable logic for splitting the code
        base_code = full_batch_code[:5]
        machine_code = full_batch_code[5:]

        product = Product.query.filter_by(sku=sku).first()
        report = None
        if product:
            report = QualityReport.query.filter_by(
                product_id=product.id,
                batch_code=base_code,
            ).order_by(QualityReport.created_at.desc()).first()

        if report:
            # Case 1: The report is linked to specific machine codes.
            if report.machine_codes:
                # If machine codes exist in the report, the user MUST enter one.
                if not machine_code:
                    error = f"This product requires a full batch code (e.g., {base_code}A1). Please enter the complete code."
                    return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, error=error)

                allowed_codes = {code.strip() for code in report.machine_codes.split(',') if code.strip()}
                if machine_code in allowed_codes:
                    ordered_results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
                    return render_template('public/report.html', report=report, results=ordered_results, machine_code=machine_code)
            
            # Case 2: The report has no machine codes.
            else:
                 # If no machine codes are on the report, the user must NOT have entered one.
                if machine_code:
                    error = "This batch code does not have a machine-specific ID. Please enter only the 5-digit batch code."
                    return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, error=error)

                ordered_results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
                return render_template('public/report.html', report=report, results=ordered_results, machine_code=machine_code)

        # If no valid report is found after all checks, show a clear error.
        error = "No report found. Please check the product and batch code details and try again."
        return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA, error=error)

    # For GET requests, render the initial page.
    return render_template('public/index.html', products=Product.query.all(), awareness_data=AWARENESS_DATA)




from urllib.parse import urlparse # Make sure to import this

@bp.route('/download/report/<int:report_id>')
def download_pdf_report(report_id):
    report = QualityReport.query.get_or_404(report_id)
    machine_code = request.args.get('machine_code', None)
    results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
    
    html_out = render_template('reports/milk_report.html', report=report, results=results, machine_code=machine_code)
    result = BytesIO()
    
    # This is the robust link_callback that fixes the problem
    def link_callback(uri, rel):
        """
        Convert HTML URIs to absolute system paths so xhtml2pdf can access them.
        """
        # Parse the URI to get just the path part (e.g., /static/logo.png)
        parsed_uri = urlparse(uri)
        path = parsed_uri.path
        
        # Check if the path is for a STATIC file
        static_url = url_for('static', filename='')
        if path.startswith(static_url):
            # Build the full, local file system path to the static file
            static_path = os.path.join(current_app.static_folder, path[len(static_url):])
            if os.path.exists(static_path):
                return static_path
        
        # Check if the path is for an UPLOADED file
        uploads_url = url_for('main.uploaded_file', filename='')
        if path.startswith(uploads_url):
            # Build the full, local file system path to the uploaded file
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], path[len(uploads_url):])
            if os.path.exists(upload_path):
                return upload_path

        # If it's any other kind of link, return it as is
        return uri

    pdf = pisa.CreatePDF(
        BytesIO(html_out.encode('UTF-8')),
        dest=result,
        link_callback=link_callback  # Use the new, robust function
    )

    if not pdf.err:
        response = make_response(result.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="quality_report_{report.batch_code}{machine_code or ''}.pdf"'
        return response
    
    # Log the error and notify the user
    print(f"PDF Generation Error: {pdf.err} for report {report_id}")
    flash('An error occurred while generating the PDF report.', 'danger')
    return redirect(url_for('main.index'))


# This route is still needed for images in the PDF template.
@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

# --- QA Routes (QA Incharge) ---
@bp.route('/qa/login', methods=['GET', 'POST'])
def qa_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.qa_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.qa_dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('qa/login.html')

@bp.route('/qa/logout')
@login_required
def qa_logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/qa/dashboard')
@login_required
def qa_dashboard():
    if current_user.role == 'superadmin':
        return redirect(url_for('main.superadmin_dashboard'))
    
    reports = QualityReport.query.filter_by(plant_name=current_user.plant_name).order_by(QualityReport.created_at.desc()).all()
    return render_template('qa/dashboard.html', reports=reports)

@bp.route('/qa/report/new', methods=['GET', 'POST'])
@login_required
def new_report():
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        batch_code = request.form.get('batch_code', '')
        expiry_date_str = request.form.get('expiry_date')
        machine_codes = request.form.get('machine_codes', '').strip()

        if not all([product_id, batch_code, expiry_date_str]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('main.new_report'))

        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        
        new_report_obj = QualityReport(
            product_id=product_id,
            user_id=current_user.id,
            batch_code=batch_code,
            machine_codes=machine_codes,
            expiry_date=expiry_date,
            plant_name=current_user.plant_name
        )
        db.session.add(new_report_obj)
        
        for key, value in request.form.items():
            if key.startswith('result-'):
                template_id = key.split('-')[1]
                result = ReportResult(
                    report=new_report_obj,
                    template_id=template_id,
                    result_value=value
                )
                db.session.add(result)
        
        db.session.commit()
        flash('New quality report created successfully!', 'success')
        return redirect(url_for('main.qa_dashboard'))

    products = Product.query.all()
    return render_template('qa/new_report.html', products=products)

@bp.route('/qa/report/delete/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    report = QualityReport.query.filter_by(id=report_id, plant_name=current_user.plant_name).first_or_404()
    db.session.delete(report)
    db.session.commit()
    flash('Report deleted successfully.', 'success')
    return redirect(url_for('main.qa_dashboard'))

@bp.route('/qa/report/edit/<int:report_id>', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    report = QualityReport.query.filter_by(id=report_id, plant_name=current_user.plant_name).first_or_404()
    
    if request.method == 'POST':
        report.product_id = request.form.get('product_id')
        report.batch_code = request.form.get('batch_code', '')
        report.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()

        for key, value in request.form.items():
            if key.startswith('result-'):
                result_id = key.split('-')[1]
                result = ReportResult.query.get(result_id)
                if result and result.report_id == report.id: # Ensure the result belongs to the report
                    result.result_value = value
        
        db.session.commit()
        flash('Quality report updated successfully!', 'success')
        return redirect(url_for('main.qa_dashboard'))

    products = Product.query.all()
    # Organize results in a dictionary for easy lookup in the template
    results_dict = {result.template_id: result for result in report.results}
    return render_template('qa/edit_report.html', report=report, products=products, results_dict=results_dict)

@bp.route('/api/templates/<int:product_id>')
@login_required
def get_templates_for_product(product_id):
    product = Product.query.get_or_404(product_id)
    templates = ReportTemplate.query.filter_by(product_id=product.id).order_by(ReportTemplate.order).all()
    
    template_list = [{
        'id': t.id,
        'parameter': t.parameter,
        'specification': t.specification,
        'method': t.method
    } for t in templates]
    
    return jsonify({'templates': template_list})


# --- Superadmin Routes ---
@bp.route('/superadmin/dashboard')
@login_required
@superadmin_required
def superadmin_dashboard():
    qa_users = User.query.filter_by(role='qa').all()
    products = Product.query.all()
    plants = Plant.query.all()
    all_reports = QualityReport.query.order_by(QualityReport.created_at.desc()).all()
    return render_template('superadmin/dashboard.html', 
                           qa_users=qa_users, 
                           products=products, 
                           plants=plants, 
                           all_reports=all_reports)

@bp.route('/superadmin/users/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        plant_name = request.form.get('plant_name')
        
        signature_file = request.files.get('signature')
        sig_filename = None
        if signature_file and signature_file.filename != '':
            sig_filename = secure_filename(f"sig_{username}_{signature_file.filename}")
            signature_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], sig_filename))

        new_user = User(username=username, plant_name=plant_name, signature_filename=sig_filename, role='qa')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'QA User "{username}" created successfully!', 'success')
        return redirect(url_for('main.superadmin_dashboard'))

    plants = Plant.query.all()
    return render_template('superadmin/user_form.html', plants=plants, form_title="Add New QA User")

@bp.route('/superadmin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.signature_filename:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], user.signature_filename))
        except OSError:
            pass
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" has been deleted.', 'success')
    return redirect(url_for('main.superadmin_dashboard'))

@bp.route('/superadmin/products/new', methods=['POST'])
@login_required
@superadmin_required
def new_product():
    name = request.form.get('product_name')
    sku = request.form.get('product_sku')
    if name and sku:
        product = Product(name=name, sku=sku)
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{name}" created successfully!', 'success')
    else:
        flash('Product Name and SKU are required.', 'danger')
    return redirect(url_for('main.superadmin_dashboard'))

@bp.route('/superadmin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" has been deleted.', 'success')
    return redirect(url_for('main.superadmin_dashboard'))

@bp.route('/superadmin/plants/new', methods=['POST'])
@login_required
@superadmin_required
def new_plant():
    name = request.form.get('plant_name')
    code = request.form.get('plant_code')
    if name and code:
        if Plant.query.filter_by(name=name).first() or Plant.query.filter_by(code=code).first():
            flash('Plant with this name or code already exists.', 'danger')
        else:
            plant = Plant(name=name, code=code)
            db.session.add(plant)
            db.session.commit()
            flash(f'Plant "{name}" created successfully!', 'success')
    else:
        flash('Plant Name and Code are required.', 'danger')
    return redirect(url_for('main.superadmin_dashboard'))

@bp.route('/superadmin/plants/delete/<int:plant_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    db.session.delete(plant)
    db.session.commit()
    flash(f'Plant "{plant.name}" has been deleted.', 'success')
    return redirect(url_for('main.superadmin_dashboard'))

@bp.route('/superadmin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_product(product_id):
    # This is a placeholder as the functionality wasn't fully implemented
    flash('Edit product functionality is not yet implemented.', 'info')
    return redirect(url_for('main.superadmin_dashboard'))

@bp.route('/superadmin/plants/edit/<int:plant_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_plant(plant_id):
    # This is a placeholder as the functionality wasn't fully implemented
    flash('Edit plant functionality is not yet implemented.', 'info')
    return redirect(url_for('main.superadmin_dashboard'))

