# project/populate_db.py
# --- CORE SCRIPT FOR ONE-TIME DATA MIGRATION ---

import click
import os
import sqlite3
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from datetime import datetime

# --- IMPORTANT: CONFIGURE THIS PATH ---
# Set this to the path of your old SQLite file. 
OLD_DB_PATH = 'app.db' 
# -------------------------------------


from . import db
from .models import (
    User, Product, ReportTemplate, QualityReport, ReportResult, 
    Plant, ParameterMaster, plant_product_association
)

# --- STATIC DATA DEFINITIONS ---

DEFAULT_PLANT_DATA = [
    {'name': 'Shamirpet', 'code': 'SH'},
    {'name': 'Uppal', 'code': 'UP'},
    {'name': 'Bangalore', 'code': 'BL'},
    {'name': 'Corporate', 'code': 'CORP'}
]

DEFAULT_SUPERUSER = {
    'username': 'superadmin',
    'password': 'password', # <<< IMPORTANT: CHANGE THIS IMMEDIATELY AFTER LOGIN >>>
    'plant_name': 'Corporate',
    'role': 'superadmin'
}
# ------------------------------------------

@click.command('populate-db')
@with_appcontext
@click.option('--clear-existing', is_flag=True, default=False, help='Clear ALL data from the new structure before population.')
def populate_db_command(clear_existing):
    """Populates the new database structure with data from the old SQLite file."""

    if not os.path.exists(OLD_DB_PATH):
        click.echo(f"Error: Old database file not found at {OLD_DB_PATH}", err=True)
        return

    # --- Setup Plant Mapping (Crucial for Migration) ---
    if not db.session.query(Plant).first():
        click.echo("Warning: No initial Plant data found. Creating default plants.")
        for plant_data in DEFAULT_PLANT_DATA:
            if not Plant.query.filter_by(name=plant_data['name']).first():
                new_plant = Plant(name=plant_data['name'], code=plant_data['code'])
                db.session.add(new_plant)
        db.session.commit()
        click.echo("Created initial Plant records.")

    plant_name_to_id = {p.name: p.id for p in Plant.query.all()}


    # --- 1. Clear Existing Data (Optional) ---
    if clear_existing:
        click.echo("Clearing existing data...")
        db.session.query(ReportResult).delete()
        db.session.query(QualityReport).delete()
        db.session.query(ReportTemplate).delete()
        db.session.query(Product).delete()
        db.session.query(User).delete()
        db.session.commit()
        click.echo("Existing data cleared.")


    # --- 2. Connect to Old Database ---
    try:
        conn = sqlite3.connect(OLD_DB_PATH)
        conn.row_factory = sqlite3.Row # Keep Row factory, but we'll convert to dict below
        old_db = conn.cursor()
    except Exception as e:
        click.echo(f"Error connecting to old database: {e}", err=True)
        return
    
    
    # --- 3. Migrate Users (with Plant ID mapping) ---
    try:
        old_users = old_db.execute('SELECT * FROM user').fetchall()
        click.echo(f"Migrating {len(old_users)} users...")
        for row in old_users:
            # FIX: Convert sqlite3.Row to dict to enable robust .get()
            row_data = dict(row)
            
            if User.query.filter_by(username=row_data['username']).first():
                continue

            plant_name = row_data['plant_name'] if row_data.get('plant_name') else 'Corporate'
            plant_id = plant_name_to_id.get(plant_name)

            new_user = User(
                id=row_data['id'], 
                username=row_data['username'],
                password_hash=row_data['password_hash'],
                role=row_data['role'],
                plant_name=plant_name,
                plant_id=plant_id, # <<< MIGRATION FIELD >>>
                # FIX: .get() now works safely
                signature_filename=row_data.get('signature_filename')
            )
            db.session.add(new_user)
        db.session.commit()
        click.echo("Users migrated successfully.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error during user migration: {e}", err=True)
    
    # --- 3.1. Ensure Superuser Exists (Your Request) ---
    try:
        superuser = User.query.filter_by(username=DEFAULT_SUPERUSER['username']).first()
        if not superuser:
            plant_id = plant_name_to_id.get(DEFAULT_SUPERUSER['plant_name'])
            
            new_superuser = User(
                username=DEFAULT_SUPERUSER['username'],
                role=DEFAULT_SUPERUSER['role'],
                plant_name=DEFAULT_SUPERUSER['plant_name'],
                plant_id=plant_id
            )
            new_superuser.set_password(DEFAULT_SUPERUSER['password'])
            db.session.add(new_superuser)
            db.session.commit()
            click.echo(f"\n--- IMPORTANT: Created guaranteed superadmin user: '{DEFAULT_SUPERUSER['username']}' with password: '{DEFAULT_SUPERUSER['password']}' ---")
        else:
            click.echo("Guaranteed superadmin user already exists.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error creating default superuser: {e}", err=True)


    # --- 4. Migrate Products, Templates, Reports, and Results (Full Logic) ---

    # 4. Products
    try:
        old_products = old_db.execute('SELECT * FROM product').fetchall()
        click.echo(f"Migrating {len(old_products)} products...")
        for row in old_products:
            row_data = dict(row)
            if Product.query.filter_by(sku=row_data['sku']).first():
                continue
            
            new_product = Product(
                id=row_data['id'],
                name=row_data['name'],
                sku=row_data['sku']
            )
            db.session.add(new_product)
        db.session.commit()
        click.echo("Products migrated successfully.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error during product migration: {e}", err=True)

    # 5. Report Templates
    try:
        old_templates = old_db.execute('SELECT * FROM report_template').fetchall()
        click.echo(f"Migrating {len(old_templates)} templates...")
        for row in old_templates:
            row_data = dict(row)
            if ReportTemplate.query.get(row_data['id']): 
                continue 
            
            new_template = ReportTemplate(
                id=row_data['id'],
                product_id=row_data['product_id'],
                parameter=row_data['parameter'],
                specification=row_data['specification'],
                method=row_data['method'],
                order=row_data['order']
            )
            db.session.add(new_template)
        db.session.commit()
        click.echo("Report Templates migrated successfully.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error during template migration: {e}", err=True)

    # 6. Quality Reports and 7. Report Results
    try:
        old_reports = old_db.execute('SELECT * FROM quality_report').fetchall()
        click.echo(f"Migrating {len(old_reports)} reports...")
        
        report_results_data = []

        for row in old_reports:
            row_data = dict(row)
            if QualityReport.query.get(row_data['id']):
                continue

            plant_name = row_data['plant_name'] if row_data.get('plant_name') else None
            plant_id = plant_name_to_id.get(plant_name)
            
            machine_codes_value = row_data.get('machine_codes')

            new_report = QualityReport(
                id=row_data['id'],
                product_id=row_data['product_id'],
                user_id=row_data['user_id'],
                batch_code=row_data['batch_code'],
                machine_codes=machine_codes_value if machine_codes_value is not None else None, 
                expiry_date=datetime.strptime(row_data['expiry_date'], '%Y-%m-%d').date(),
                plant_name=plant_name,
                plant_id=plant_id,
                created_at=datetime.strptime(row_data['created_at'], '%Y-%m-%d %H:%M:%S.%f')
            )
            db.session.add(new_report)

            old_results = old_db.execute(f'SELECT * FROM report_result WHERE report_id={row_data["id"]}').fetchall()
            for r_row in old_results:
                report_results_data.append(dict(r_row))

        db.session.commit()
        click.echo("Quality Reports migrated successfully.")

        click.echo(f"Migrating {len(report_results_data)} report results...")
        for r_row in report_results_data:
            if ReportResult.query.get(r_row['id']):
                continue

            new_result = ReportResult(
                id=r_row['id'],
                report_id=r_row['report_id'],
                template_id=r_row['template_id'],
                result_value=r_row['result_value']
            )
            db.session.add(new_result)
        db.session.commit()
        click.echo("Report Results migrated successfully.")

    except Exception as e:
        db.session.rollback()
        click.echo(f"Error during report/result migration: {e}", err=True)
        
    # 8. Populate Missing ParameterMaster Records
    try:
        click.echo("Populating default ParameterMaster records...")
        
        default_templates = old_db.execute('SELECT DISTINCT parameter, method FROM report_template').fetchall()
        
        for row in default_templates:
            row_data = dict(row)
            param_name = row_data['parameter']
            param_method = row_data['method']
            
            if not ParameterMaster.query.filter_by(name=param_name).first():
                new_master = ParameterMaster(
                    name=param_name,
                    default_method=param_method
                )
                db.session.add(new_master)
        
        db.session.commit()
        click.echo("ParameterMaster data populated based on old templates.")
        
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error populating ParameterMaster: {e}", err=True)
        

    conn.close()
    click.echo("\nDatabase population complete. Review console output for any errors.")

def init_app(app):
    """Register this command with the Flask app."""
    app.cli.add_command(populate_db_command)