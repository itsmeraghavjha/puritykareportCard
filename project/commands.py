# # Defines custom Flask CLI commands.

# import click
# from flask.cli import with_appcontext
# from . import db
# from .models import User, Product, ReportTemplate, QualityReport, ReportResult
# from datetime import date

# @click.command('init-db')
# @with_appcontext
# def init_db_command():
#     """Clear the existing data and create new tables."""
#     db.create_all()
#     click.echo('Initialized the database.')

#     # Create users if they don't exist
#     if not User.query.filter_by(username='admin_shamirpet').first():
#         admin_shamirpet = User(
#             username='admin_shamirpet',
#             plant_name='Shamirpet',
#             signature_filename='Shamirpet_signature.png'
#         )
#         admin_shamirpet.set_password('password_s')
#         db.session.add(admin_shamirpet)

#     if not User.query.filter_by(username='admin_uppal').first():
#         admin_uppal = User(
#             username='admin_uppal',
#             plant_name='Uppal',
#             signature_filename='Uppal_signature.png'
#         )
#         admin_uppal.set_password('password_u')
#         db.session.add(admin_uppal)

#     db.session.commit()
#     click.echo('Created initial users.')

#     # Create products and templates if they don't exist
#     if not Product.query.first():
#         pbm = Product(name='Pasteurised Buffalo Milk', sku='PBM_500')
#         pcm = Product(name='Sampoorna Cow Milk', sku='PCM_500')
#         db.session.add_all([pbm, pcm])
#         db.session.commit()
#         click.echo('Created initial products.')

#         # Add templates for products
#         # ... (template creation logic from your initial_data.py)

#     click.echo('Database initialization complete.')

# def init_app(app):
#     app.cli.add_command(init_db_command)



# Defines custom Flask CLI commands.

import click
from flask.cli import with_appcontext
from . import db
from .models import User, Product, ReportTemplate, QualityReport, ReportResult
from datetime import date



# --- BEST PRACTICE: Enhanced the dedicated command to create users ---
@click.command('create-user')
@with_appcontext
@click.option('--username', prompt=True, help='The username for the new user.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password for the new user.')
@click.option('--role', prompt='User role (qa or superadmin)', default='qa', type=click.Choice(['qa', 'superadmin']), help='The role for the new user.')
def create_user_command(username, password, role):
    """(SAFE) Creates a new user interactively."""
    
    # Check if username exists
    if User.query.filter_by(username=username).first():
        click.echo(f"Error: User '{username}' already exists.")
        return

    plant_name = None
    signature_filename = None

    if role == 'qa':
        # QA users require a plant and signature
        plant_name = click.prompt('Plant name (e.g., Shamirpet, Uppal)')
        signature_input = click.prompt('Signature Filename (optional, press Enter to skip)', default='')
        signature_filename = signature_input.strip() if signature_input.strip() else None
    else:
        # Superadmin is not tied to a plant.
        # We must provide a value because the DB column is not nullable.
        # 'Corporate' is a sensible default.
        plant_name = 'Corporate' 
        click.echo(f"Creating superadmin. Plant set to '{plant_name}'.")

    # Create new user
    new_user = User(
        username=username,
        plant_name=plant_name,
        role=role,
        signature_filename=signature_filename
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    click.echo(f"Successfully created {role} user '{username}'.")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.create_all()
    click.echo('Initialized the database.')

    # Create users if they don't exist
    if not User.query.filter_by(username='admin_shamirpet').first():
        admin_shamirpet = User(
            username='admin_shamirpet',
            plant_name='Shamirpet',
            signature_filename='Shamirpet_signature.png'
        )
        admin_shamirpet.set_password('password_s')
        db.session.add(admin_shamirpet)

    if not User.query.filter_by(username='admin_uppal').first():
        admin_uppal = User(
            username='admin_uppal',
            plant_name='Uppal',
            signature_filename='Uppal_signature.png'
        )
        admin_uppal.set_password('password_u')
        db.session.add(admin_uppal)

    db.session.commit()
    click.echo('Created initial users.')

    # Create products and templates if they don't exist
    if not Product.query.first():
        pbm = Product(name='Pasteurised Buffalo Milk', sku='PBM_500')
        pcm = Product(name='Sampoorna Cow Milk', sku='PCM_500')
        db.session.add_all([pbm, pcm])
        db.session.commit()
        click.echo('Created initial products.')

        # Add templates for Pasteurised Buffalo Milk
        pbm_templates = [
            ReportTemplate(product=pbm, parameter='Appearance & Colour', specification='White, Uniform', method='Visual', order=1),
            ReportTemplate(product=pbm, parameter='Physical State', specification='Homogeneous liquid, free from extraneous matter', method='Visual', order=2),
            ReportTemplate(product=pbm, parameter='Odour & Flavour', specification='Pleasant, free from offodors', method='Sensory', order=3),
            ReportTemplate(product=pbm, parameter='Taste', specification='Mildly sweet, no sour or bitter taste', method='Sensory', order=4),
            ReportTemplate(product=pbm, parameter='Fat % (Min)', specification='7', method='Gerber -FSSAI', order=5),
            ReportTemplate(product=pbm, parameter='SNF % (Min)', specification='9', method='FSSAI', order=6),
            ReportTemplate(product=pbm, parameter='Protein %', specification='Min 36 % on MSNF', method='Milk analyser', order=7),
            ReportTemplate(product=pbm, parameter='Titratable Acidity % (La)', specification='Max. 0.14', method='FSSAI', order=8),
            ReportTemplate(product=pbm, parameter='Heat Stability (HS)', specification='Min 0.5ml', method='ISO', order=9),
            ReportTemplate(product=pbm, parameter='Heat Stability (Alcohol)', specification='Min 60 %', method='ISO', order=10),
            ReportTemplate(product=pbm, parameter='COB', specification='Negative', method='FSSAI', order=11),
            ReportTemplate(product=pbm, parameter='MBRT(hrs)', specification='Min 6.0 hrs', method='FSSAI', order=12),
            ReportTemplate(product=pbm, parameter='Phosphatase test', specification='Negative', method='FSSAI', order=13),
            ReportTemplate(product=pbm, parameter='Total Sodium / 100 gm SNF', specification='Max 550 mg', method='Analyser', order=14),
            ReportTemplate(product=pbm, parameter='Cane Sugar(Sucrose)', specification='Negative', method='FSSAI', order=15),
            ReportTemplate(product=pbm, parameter='Salt', specification='Negative', method='FSSAI', order=16),
            ReportTemplate(product=pbm, parameter='Starch', specification='Negative', method='FSSAI', order=17),
            ReportTemplate(product=pbm, parameter='Added Urea', specification='Negative', method='FSSAI', order=18),
            ReportTemplate(product=pbm, parameter='Maltodextrin', specification='Negative', method='FSSAI', order=19),
            ReportTemplate(product=pbm, parameter='Formalin', specification='Negative', method='FSSAI', order=20),
            ReportTemplate(product=pbm, parameter='Hydrogen Peroxide', specification='Negative', method='FSSAI', order=21),
            ReportTemplate(product=pbm, parameter='Neutralizers', specification='Negative', method='FSSAI', order=22),
            ReportTemplate(product=pbm, parameter='Glucose', specification='Negative', method='FSSAI', order=23),
            ReportTemplate(product=pbm, parameter='Detergent', specification='Negative', method='FSSAI', order=24),
            ReportTemplate(product=pbm, parameter='Ammonium Sulphate', specification='Negative', method='FSSAI', order=25),
            ReportTemplate(product=pbm, parameter='Fat B.R reading at 40 Deg C', specification='40-44', method='FSSAI', order=26),
        ]

        # Add templates for Sampoorna Cow Milk
        pcm_templates = [
            ReportTemplate(product=pcm, parameter='Appearance & Colour', specification='Slightly yellow, uniform', method='Visual', order=1),
            ReportTemplate(product=pcm, parameter='Physical State', specification='Homogeneous liquid, free from extraneous matter', method='Visual', order=2),
            ReportTemplate(product=pcm, parameter='Odour & Flavour', specification='Pleasant, free from offodors', method='Sensory', order=3),
            ReportTemplate(product=pcm, parameter='Taste', specification='Mildly salty, no sour or bitter taste', method='Sensory', order=4),
            ReportTemplate(product=pcm, parameter='Fat % (Min)', specification='4', method='Gerber -FSSAI', order=5),
            ReportTemplate(product=pcm, parameter='SNF % (Min)', specification='8.5', method='FSSAI', order=6),
            ReportTemplate(product=pcm, parameter='Protein %', specification='Min 34 % on MSNF', method='Milk analyser', order=7),
            ReportTemplate(product=pcm, parameter='Titratable Acidity % (La)', specification='0.14', method='FSSAI', order=8),
            ReportTemplate(product=pcm, parameter='Heat Stability (HS)', specification='Min 0.5ml', method='ISO', order=9),
            ReportTemplate(product=pcm, parameter='Heat Stability (Alcohol)', specification='Min 60 %', method='ISO', order=10),
            ReportTemplate(product=pcm, parameter='COB', specification='Negative', method='FSSAI', order=11),
            ReportTemplate(product=pcm, parameter='MBRT(hrs)', specification='Min 6.0hrs', method='FSSAI', order=12),
            ReportTemplate(product=pcm, parameter='Phosphatase test', specification='Negative', method='FSSAI', order=13),
            ReportTemplate(product=pcm, parameter='Total Sodium / 100 gm SNF', specification='Max 550 mg', method='Analyser', order=14),
            ReportTemplate(product=pcm, parameter='Cane Sugar(Sucrose)', specification='Negative', method='FSSAI', order=15),
            ReportTemplate(product=pcm, parameter='Salt', specification='Negative', method='FSSAI', order=16),
            ReportTemplate(product=pcm, parameter='Starch', specification='Negative', method='FSSAI', order=17),
            ReportTemplate(product=pcm, parameter='Added Urea', specification='Negative', method='FSSAI', order=18),
            ReportTemplate(product=pcm, parameter='Maltodextrin', specification='Negative', method='FSSAI', order=19),
            ReportTemplate(product=pcm, parameter='Formalin', specification='Negative', method='FSSAI', order=20),
            ReportTemplate(product=pcm, parameter='Hydrogen Peroxide', specification='Negative', method='FSSAI', order=21),
            ReportTemplate(product=pcm, parameter='Neutralizers', specification='Negative', method='FSSAI', order=22),
            ReportTemplate(product=pcm, parameter='Glucose', specification='Negative', method='FSSAI', order=23),
            ReportTemplate(product=pcm, parameter='Detergent', specification='Negative', method='FSSAI', order=24),
            ReportTemplate(product=pcm, parameter='Ammonium Sulphate', specification='Negative', method='FSSAI', order=25),
            ReportTemplate(product=pcm, parameter='Fat B.R reading at 40 Deg. C', specification='40-44', method='FSSAI', order=26),
        ]

        db.session.add_all(pbm_templates)
        db.session.add_all(pcm_templates)
        db.session.commit()
        click.echo('Created initial product templates.')

    click.echo('Database initialization complete.')

def init_app(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_user_command)
