# project/routes.py
# Contains all application routes, organized by blueprints.

import os
from flask import (Blueprint, render_template, request, redirect, url_for, 
                   flash, current_app, make_response, send_from_directory, jsonify)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta # <-- Added timedelta for analytics
from functools import wraps

from . import db
# Import AnalyticsEvent and sqlalchemy.func
from .models import (Product, QualityReport, ReportTemplate, User, Plant, 
                     ReportResult, ParameterMaster, AnalyticsEvent)
from sqlalchemy import func
from .data import AWARENESS_DATA
from .utils import generate_report_pdf

from xhtml2pdf import pisa
from io import BytesIO

bp = Blueprint('main', __name__)


# --- Analytics Helper ---
def log_event(event_type):
    """
    Logs an analytics event to the database.
    This is wrapped in a try/except to ensure that analytics
    failures never crash a user-facing request.
    """
    try:
        ip = request.remote_addr
        user_agent = request.user_agent.string
        
        event = AnalyticsEvent(
            event_type=event_type,
            ip_address=ip,
            user_agent=user_agent
        )
        
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log this error to your console/server logs, but don't stop the request
        current_app.logger.error(f"Analytics logging failed: {e}")
# --- End Analytics Helper ---


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

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        log_event('PAGE_VIEW')

    if request.method == 'POST':
        full_batch_code = request.form.get('batch-code', '').strip().upper()

        if not full_batch_code or len(full_batch_code) < 5:
            error = "Please enter a valid Batch Code (at least 5 characters)."
            return render_template('public/index.html', awareness_data=AWARENESS_DATA, error=error)

        base_code = full_batch_code[:5]
        machine_code = full_batch_code[5:]

        report = QualityReport.query.filter_by(
            batch_code=base_code
        ).order_by(QualityReport.created_at.desc()).first()
        
        if report:
            if report.machine_codes:
                if not machine_code:
                    error = f"This product requires a full batch code (e.g., {base_code}A1). Please enter the complete code."
                    return render_template('public/index.html', awareness_data=AWARENESS_DATA, error=error)

                allowed_codes = {code.strip() for code in report.machine_codes.split(',') if code.strip()}
                if machine_code in allowed_codes:
                    log_event('REPORT_VIEW')
                    ordered_results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
                    return render_template('public/report.html', report=report, results=ordered_results, machine_code=machine_code)
            
            else:
                if machine_code:
                    error = "This batch code does not have a machine-specific ID. Please enter only the 5-digit batch code."
                    return render_template('public/index.html', awareness_data=AWARENESS_DATA, error=error)

                log_event('REPORT_VIEW')
                ordered_results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
                return render_template('public/report.html', report=report, results=ordered_results, machine_code=machine_code)

        error = "No report found. Please check the batch code and try again."
        return render_template('public/index.html', awareness_data=AWARENESS_DATA, error=error)

    return render_template('public/index.html', awareness_data=AWARENESS_DATA)


from urllib.parse import urlparse 

@bp.route('/download/report/<int:report_id>')
def download_pdf_report(report_id):
    report = QualityReport.query.get_or_404(report_id)
    
    log_event('REPORT_DOWNLOAD')
    
    machine_code = request.args.get('machine_code', None)
    results = report.results.join(ReportTemplate).order_by(ReportTemplate.order).all()
    
    html_out = render_template('reports/milk_report.html', report=report, results=results, machine_code=machine_code)
    result = BytesIO()
    
    def link_callback(uri, rel):
        parsed_uri = urlparse(uri)
        path = parsed_uri.path
        
        static_url = url_for('static', filename='')
        if path.startswith(static_url):
            static_path = os.path.join(current_app.static_folder, path[len(static_url):])
            if os.path.exists(static_path):
                return static_path
        
        uploads_url = url_for('main.uploaded_file', filename='')
        if path.startswith(uploads_url):
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], path[len(uploads_url):])
            if os.path.exists(upload_path):
                return upload_path

        return uri

    pdf = pisa.CreatePDF(
        BytesIO(html_out.encode('UTF-8')),
        dest=result,
        link_callback=link_callback
    )

    if not pdf.err:
        response = make_response(result.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="quality_report_{report.batch_code}{machine_code or ''}.pdf"'
        return response
    
    print(f"PDF Generation Error: {pdf.err} for report {report_id}")
    flash('An error occurred while generating the PDF report.', 'danger')
    return redirect(url_for('main.index'))


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
    
    # ---
    # MODIFICATION: Implement pagination
    # ---
    # Get the page number from the URL query, default to 1
    page = request.args.get('page', 1, type=int)
    # Define how many reports to show per page
    PER_PAGE = 20 

    # Change the query from .all() to .paginate()
    pagination = QualityReport.query.filter_by(
        plant_name=current_user.plant_name
    ).order_by(
        QualityReport.created_at.desc()
    ).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    # --- END MODIFICATION ---

    # Pass the whole pagination object to the template
    return render_template('qa/dashboard.html', pagination=pagination)


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
            plant_name=current_user.plant_name,
            plant_id=current_user.plant_id # Make sure plant_id is set
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

    products = Product.query.join(Product.plants).filter(Plant.id == current_user.plant_id).order_by(Product.name).all()
    return render_template('qa/new_report.html', products=products)

@bp.route('/qa/report/delete/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    # QA users should only be able to delete reports from their own plant
    report = QualityReport.query.filter_by(id=report_id, plant_id=current_user.plant_id).first_or_404()
    db.session.delete(report)
    db.session.commit()
    flash('Report deleted successfully.', 'success')
    return redirect(url_for('main.qa_dashboard'))

@bp.route('/qa/report/edit/<int:report_id>', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    # QA users should only be able to edit reports from their own plant
    report = QualityReport.query.filter_by(id=report_id, plant_id=current_user.plant_id).first_or_404()
    
    if request.method == 'POST':
        report.product_id = request.form.get('product_id')
        report.batch_code = request.form.get('batch_code', '')
        report.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
        report.machine_codes = request.form.get('machine_codes', '').strip() # Added machine_codes

        for key, value in request.form.items():
            if key.startswith('result-'):
                result_id = key.split('-')[1]
                result = ReportResult.query.get(result_id)
                if result and result.report_id == report.id: # Ensure the result belongs to the report
                    result.result_value = value
        
        db.session.commit()
        flash('Quality report updated successfully!', 'success')
        return redirect(url_for('main.qa_dashboard'))

    # Ensure the correct products (for this user's plant) are available in the dropdown
    products = Product.query.join(Product.plants).filter(Plant.id == current_user.plant_id).order_by(Product.name).all()
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
        'method': t.method,
        'order': t.order
    } for t in templates]

    return jsonify({'templates': template_list})

# --- Superadmin Routes ---
@bp.route('/superadmin/dashboard')
@login_required
@superadmin_required
def superadmin_dashboard():
    
    # 1. Existing Data
    qa_users = User.query.filter_by(role='qa').all()
    products = Product.query.all()
    plants = Plant.query.all()
    master_parameters = ParameterMaster.query.order_by(ParameterMaster.name).all()
    all_reports = QualityReport.query.order_by(QualityReport.created_at.desc()).all()

    # 2. Internal Counts (Your request)
    analytics_data = {
        'plant_count': len(plants),
        'product_count': len(products),
        'template_count': db.session.query(ReportTemplate.id).count(),
        'qa_user_count': len(qa_users),
        'total_reports': len(all_reports)
    }

    # 3. Consumer Stats (Your request)
    analytics_data['total_page_views'] = db.session.query(AnalyticsEvent.id).filter_by(event_type='PAGE_VIEW').count()
    analytics_data['total_report_views'] = db.session.query(AnalyticsEvent.id).filter_by(event_type='REPORT_VIEW').count()
    analytics_data['total_downloads'] = db.session.query(AnalyticsEvent.id).filter_by(event_type='REPORT_DOWNLOAD').count()
    
    # Approx. unique visitors (by IP)
    analytics_data['unique_visitors'] = db.session.query(AnalyticsEvent.ip_address).distinct().count()

    # 4. Data for Time-Series Chart (NEW)
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29) # 30 days ago (inclusive of today)
    
    # Create a list of all 30 date labels
    date_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    # Query the DB for all events in the last 30 days, grouped by date and type
    raw_data = db.session.query(
        func.date(AnalyticsEvent.timestamp),
        AnalyticsEvent.event_type,
        func.count(AnalyticsEvent.id)
    ).filter(
        AnalyticsEvent.timestamp >= start_date
    ).filter(
        AnalyticsEvent.event_type.in_(['PAGE_VIEW', 'REPORT_VIEW', 'REPORT_DOWNLOAD'])
    ).group_by(
        func.date(AnalyticsEvent.timestamp),
        AnalyticsEvent.event_type
    ).all()
    
    # Process the raw data into a format Chart.js can read
    # Initialize a dict with all dates set to 0
    processed_data = {label: {'PAGE_VIEW': 0, 'REPORT_VIEW': 0, 'REPORT_DOWNLOAD': 0} for label in date_labels}
    
    # Fill in the counts from the query
    for row in raw_data:
        date_str = row[0] # This is a string from func.date() in SQLite
        event_type = row[1]
        count = row[2]
        if date_str in processed_data:
            if event_type in processed_data[date_str]:
                processed_data[date_str][event_type] = count
                
    # Create the final data structure for the chart
    analytics_data['time_series_chart'] = {
        'labels': date_labels,
        'page_views': [processed_data[date]['PAGE_VIEW'] for date in date_labels],
        'report_views': [processed_data[date]['REPORT_VIEW'] for date in date_labels],
        'downloads': [processed_data[date]['REPORT_DOWNLOAD'] for date in date_labels]
    }
    

    return render_template('superadmin/dashboard.html', 
                           qa_users=qa_users, 
                           products=products, 
                           plants=plants,
                           master_parameters=master_parameters,
                           all_reports=all_reports,
                           analytics_data=analytics_data) 

@bp.route('/superadmin/users/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        plant_id = request.form.get('plant_id') # Get plant_id from form
        
        # Get the corresponding plant object
        plant = Plant.query.get(plant_id)
        if not plant:
            flash('Invalid plant selected.', 'danger')
            plants = Plant.query.all()
            return render_template('superadmin/user_form.html', plants=plants, form_title="Add New QA User")

        signature_file = request.files.get('signature')
        sig_filename = None
        if signature_file and signature_file.filename != '':
            sig_filename = secure_filename(f"sig_{username}_{signature_file.filename}")
            signature_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], sig_filename))

        new_user = User(
            username=username, 
            plant_name=plant.name,  # Store plant name
            plant_id=plant.id,      # Store plant ID
            signature_filename=sig_filename, 
            role='qa'
        )
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

@bp.route('/superadmin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'qa':
        flash('You can only edit QA users.', 'danger')
        return redirect(url_for('main.superadmin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        plant_id = request.form.get('plant_id') # Get plant_id
        
        # Get plant object
        plant = Plant.query.get(plant_id)
        if not plant:
            flash('Invalid plant selected.', 'danger')
            plants = Plant.query.all()
            return render_template('superadmin/user_form.html', plants=plants, user=user, form_title="Edit QA User")

        # Check if username is being changed to one that already exists
        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            flash('That username is already taken.', 'danger')
            plants = Plant.query.all()
            return render_template('superadmin/user_form.html', plants=plants, user=user, form_title="Edit QA User")

        user.username = username
        user.plant_name = plant.name # Update plant name
        user.plant_id = plant.id     # Update plant ID
        
        # Only update password if a new one was provided
        if password:
            user.set_password(password)

        signature_file = request.files.get('signature')
        if signature_file and signature_file.filename != '':
            # Delete old signature if it exists
            if user.signature_filename:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], user.signature_filename))
                except OSError:
                    pass # Ignore if file doesn't exist
            
            # Save new signature
            sig_filename = secure_filename(f"sig_{username}_{signature_file.filename}")
            signature_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], sig_filename))
            user.signature_filename = sig_filename

        db.session.commit()
        flash(f'User "{username}" updated successfully!', 'success')
        return redirect(url_for('main.superadmin_dashboard'))

    plants = Plant.query.all()
    return render_template('superadmin/user_form.html', plants=plants, user=user, form_title="Edit QA User")

@bp.route('/superadmin/products/new', methods=['POST'])
@login_required
@superadmin_required
def new_product():
    name = request.form.get('product_name')
    sku = request.form.get('product_sku')
    
    copy_from_name = request.form.get('copy_from_product_name')

    selected_plant_ids = request.form.getlist('plants', type=int)

    if name and sku:
        if Product.query.filter_by(sku=sku).first():
            flash(f'Error: Product SKU "{sku}" already exists.', 'danger')
            return redirect(url_for('main.superadmin_dashboard', tab='products'))

        product = Product(name=name, sku=sku)
        
        if selected_plant_ids:
            selected_plants = Plant.query.filter(Plant.id.in_(selected_plant_ids)).all()
            product.plants = selected_plants
        
        db.session.add(product)
        
        if copy_from_name:
            try:
                source_product = Product.query.filter_by(name=copy_from_name).first()

                if source_product:
                    source_templates = ReportTemplate.query.filter_by(product_id=source_product.id).all()

                    if source_templates:
                        new_templates = []
                        for t in source_templates:
                            new_t = ReportTemplate(
                                product=product,
                                parameter=t.parameter,
                                specification=t.specification,
                                method=t.method,
                                order=t.order
                            )
                            new_templates.append(new_t)
                        
                        db.session.add_all(new_templates)
                        flash(f'Successfully copied {len(new_templates)} templates from {source_product.name}.', 'info')
                else:
                    flash(f'Warning: Could not find product "{copy_from_name}" to copy templates from. Product was created without templates.', 'warning')

            except Exception as e:
                db.session.rollback() 
                flash(f'Error copying templates: {e}', 'danger')
                return redirect(url_for('main.superadmin_dashboard', tab='products'))
        
        db.session.commit()
        
        if copy_from_name:
             flash(f'Product "{name}" created!', 'success')
             return redirect(url_for('main.superadmin_dashboard', tab='products'))
        else:
            flash(f'Product "{name}" created! Now, please add its test templates.', 'success')
            return redirect(url_for('main.superadmin_dashboard', tab='templates', product_id=product.id))
    else:
        flash('Product Name and SKU are required.', 'danger')
    
    return redirect(url_for('main.superadmin_dashboard', tab='products'))


@bp.route('/superadmin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" has been deleted.', 'success')
    return redirect(url_for('main.superadmin_dashboard'))


@bp.route('/superadmin/templates/add/<int:product_id>', methods=['POST'])
@login_required
@superadmin_required
def add_template(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        new_template = ReportTemplate(
            product_id=product.id,
            parameter=request.form.get('parameter'),
            specification=request.form.get('specification'),
            method=request.form.get('method'),
            order=int(request.form.get('order'))
        )
        db.session.add(new_template)
        db.session.commit()
        
        template_data = {
            'id': new_template.id,
            'parameter': new_template.parameter,
            'specification': new_template.specification,
            'method': new_template.method,
            'order': new_template.order
        }
        return jsonify({'success': True, 'template': template_data})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# In project/routes.py

# In project/routes.py

# In project/routes.py

@bp.route('/superadmin/templates/delete/<int:template_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_template(template_id):
    template = ReportTemplate.query.get_or_404(template_id)
    try:
        # Get the ID before we delete it, so we can send it back to Alpine.js
        template_id_copy = template.id  
        
        db.session.delete(template)
        db.session.commit()
        
        # --- THIS IS THE FIX ---
        # Send a JSON response on success, which your HTML is waiting for
        return jsonify({'success': True, 'template_id': template_id_copy})
        
    except Exception as e:
        db.session.rollback()
        
        # Send a JSON error response
        return jsonify({'success': False, 'error': str(e)}), 500

    # The old "flash" and "redirect" are no longer used

# --- MASTER PARAMETER ROUTES ---

@bp.route('/superadmin/master_parameters/add', methods=['POST'])
@login_required
@superadmin_required
def new_master_parameter():
    try:
        new_param = ParameterMaster(
            name=request.form.get('name'),
            default_method=request.form.get('default_method')
        )
        db.session.add(new_param)
        db.session.commit()
        flash(f'Master Parameter "{new_param.name}" added.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: Could not add parameter. It might already exist. {e}', 'danger')
    return redirect(url_for('main.superadmin_dashboard', tab='master_parameters'))

@bp.route('/superadmin/master_parameters/delete/<int:param_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_master_parameter(param_id):
    param = ParameterMaster.query.get_or_404(param_id)
    try:
        db.session.delete(param)
        db.session.commit()
        flash(f'Master Parameter "{param.name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: Could not delete parameter. It might be in use. {e}', 'danger')
    return redirect(url_for('main.superadmin_dashboard', tab='master_parameters'))

@bp.route('/api/master_parameters')
@login_required
@superadmin_required
def get_master_parameters():
    params = ParameterMaster.query.all()
    param_list = [{'name': p.name, 'method': p.default_method} for p in params]
    return jsonify(param_list)

# --- END MASTER PARAMETER ROUTES ---


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
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('product_name')
        product.sku = request.form.get('product_sku')
        
        selected_plant_ids = request.form.getlist('plants', type=int)
        selected_plants = Plant.query.filter(Plant.id.in_(selected_plant_ids)).all()
        product.plants = selected_plants
        
        try:
            db.session.commit()
            flash(f'Product "{product.name}" updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: Could not update product. {e}', 'danger')
        return redirect(url_for('main.superadmin_dashboard', tab='products')) 

    all_plants = Plant.query.order_by(Plant.name).all()
    
    return render_template('superadmin/edit_product.html', product=product, all_plants=all_plants)


@bp.route('/superadmin/plants/edit/<int:plant_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    if request.method == 'POST':
        plant.name = request.form.get('plant_name')
        plant.code = request.form.get('plant_code')
        try:
            db.session.commit()
            flash(f'Plant "{plant.name}" updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: Could not update plant. Name or Code might already exist. {e}', 'danger')
        return redirect(url_for('main.superadmin_dashboard'))

    return render_template('superadmin/edit_plant.html', plant=plant)