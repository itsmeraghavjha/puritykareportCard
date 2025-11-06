# project/commands.py
# Defines custom Flask CLI commands.

import click
from flask.cli import with_appcontext
from . import db
from .models import User, Product, ReportTemplate, Plant, ParameterMaster
from datetime import date

# --- STATIC DATA DEFINITIONS (Used by init-db and populate-db) ---

INITIAL_PLANT_DATA = [
    {'name': 'Shamirpet', 'code': 'SH'},
    {'name': 'Uppal', 'code': 'UP'},
    {'name': 'Bangalore', 'code': 'BL'},
    {'name': 'Corporate', 'code': 'CORP'}
]

def generate_default_templates(product, is_cow_milk=False):
    """Generates the 26 standard templates for a product."""
    if is_cow_milk:
        templates_data = [
            # Quality & Safety (Cow Milk Specs)
            ('Appearance & Colour', 'Slightly yellow, uniform', 'Visual', 1),
            ('Physical State', 'Homogeneous liquid, free from extraneous matter', 'Visual', 2),
            ('Odour & Flavour', 'Pleasant, free from offodors', 'Sensory', 3),
            ('Taste', 'Mildly salty, no sour or bitter taste', 'Sensory', 4),
            ('Fat % (Min)', '4', 'Gerber -FSSAI', 5),
            ('SNF % (Min)', '8.5', 'FSSAI', 6),
            ('Protein %', 'Min 34 % on MSNF', 'Milk analyser', 7),
            ('Titratable Acidity % (La)', '0.14', 'FSSAI', 8),
            ('Heat Stability (HS)', 'Min 0.5ml', 'ISO', 9),
            ('Heat Stability (Alcohol)', 'Min 60 %', 'ISO', 10),
            ('COB', 'Negative', 'FSSAI', 11),
            ('MBRT(hrs)', 'Min 6.0hrs', 'FSSAI', 12),
        ]
    else:
        templates_data = [
            # Quality & Safety (Buffalo Milk Specs)
            ('Appearance & Colour', 'White, Uniform', 'Visual', 1),
            ('Physical State', 'Homogeneous liquid, free from extraneous matter', 'Visual', 2),
            ('Odour & Flavour', 'Pleasant, free from offodors', 'Sensory', 3),
            ('Taste', 'Mildly sweet, no sour or bitter taste', 'Sensory', 4),
            ('Fat % (Min)', '7', 'Gerber -FSSAI', 5),
            ('SNF % (Min)', '9', 'FSSAI', 6),
            ('Protein %', 'Min 36 % on MSNF', 'Milk analyser', 7),
            ('Titratable Acidity % (La)', 'Max. 0.14', 'FSSAI', 8),
            ('Heat Stability (HS)', 'Min 0.5ml', 'ISO', 9),
            ('Heat Stability (Alcohol)', 'Min 60 %', 'ISO', 10),
            ('COB', 'Negative', 'FSSAI', 11),
            ('MBRT(hrs)', 'Min 6.0 hrs', 'FSSAI', 12),
        ]

    # Adulteration Checks (Common for both)
    templates_data += [
        ('Phosphatase test', 'Negative', 'FSSAI', 13),
        ('Total Sodium / 100 gm SNF', 'Max 550 mg', 'Analyser', 14),
        ('Cane Sugar(Sucrose)', 'Negative', 'FSSAI', 15),
        ('Salt', 'Negative', 'FSSAI', 16),
        ('Starch', 'Negative', 'FSSAI', 17),
        ('Added Urea', 'Negative', 'FSSAI', 18),
        ('Maltodextrin', 'Negative', 'FSSAI', 19),
        ('Formalin', 'Negative', 'FSSAI', 20),
        ('Hydrogen Peroxide', 'Negative', 'FSSAI', 21),
        ('Neutralizers', 'Negative', 'FSSAI', 22),
        ('Glucose', 'Negative', 'FSSAI', 23),
        ('Detergent', 'Negative', 'FSSAI', 24),
        ('Ammonium Sulphate', 'Negative', 'FSSAI', 25),
        ('Fat B.R reading at 40 Deg C', '40-44', 'FSSAI', 26),
    ]

    new_templates = []
    for order, (param, spec, method, _) in enumerate(templates_data, 1):
        new_templates.append(
            ReportTemplate(
                product=product,
                parameter=param,
                specification=spec,
                method=method,
                order=order
            )
        )
    return new_templates

# --- END STATIC DATA DEFINITIONS ---


# --- Custom Commands ---

@click.command('create-user')
@with_appcontext
@click.option('--username', prompt=True, help='The username for the new user.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password for the new user.')
@click.option('--role', prompt='User role (qa or superadmin)', default='qa', type=click.Choice(['qa', 'superadmin']), help='The role for the new user.')
def create_user_command(username, password, role):
    """(SAFE) Creates a new user interactively."""
    
    if User.query.filter_by(username=username).first():
        click.echo(f"Error: User '{username}' already exists.")
        return

    plant_name = None
    plant_id = None
    signature_filename = None

    if role == 'qa':
        plant_name_input = click.prompt('Plant name (e.g., Shamirpet, Uppal)')
        plant = Plant.query.filter_by(name=plant_name_input).first()
        if not plant:
            click.echo(f"Error: Plant '{plant_name_input}' not found. Create it first or choose a valid name.")
            return
        plant_name = plant.name
        plant_id = plant.id
        signature_input = click.prompt('Signature Filename (optional, press Enter to skip)', default='')
        signature_filename = signature_input.strip() if signature_input.strip() else None
    else:
        plant_name = 'Corporate' 
        plant = Plant.query.filter_by(name='Corporate').first()
        if plant:
             plant_id = plant.id
        click.echo(f"Creating superadmin. Plant set to '{plant_name}'.")

    # Create new user
    new_user = User(
        username=username,
        plant_name=plant_name,
        plant_id=plant_id,
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

    # --- 1. Create Default Plants ---
    if not db.session.query(Plant).first():
        for plant_data in INITIAL_PLANT_DATA:
            db.session.add(Plant(name=plant_data['name'], code=plant_data['code']))
        db.session.commit()
        click.echo('Created initial Plants.')
    
    # Get plant IDs for initial users
    shamirpet_plant = Plant.query.filter_by(name='Shamirpet').first()
    uppal_plant = Plant.query.filter_by(name='Uppal').first()
    
    # --- 2. Create Initial QA Users ---
    if not User.query.filter_by(username='admin_shamirpet').first() and shamirpet_plant:
        admin_shamirpet = User(
            username='admin_shamirpet',
            plant_name=shamirpet_plant.name,
            plant_id=shamirpet_plant.id,
            signature_filename='Shamirpet_signature.png'
        )
        admin_shamirpet.set_password('password_s')
        db.session.add(admin_shamirpet)

    if not User.query.filter_by(username='admin_uppal').first() and uppal_plant:
        admin_uppal = User(
            username='admin_uppal',
            plant_name=uppal_plant.name,
            plant_id=uppal_plant.id,
            signature_filename='Uppal_signature.png'
        )
        admin_uppal.set_password('password_u')
        db.session.add(admin_uppal)

    db.session.commit()
    click.echo('Created initial users.')

    # --- 3. Create Products and Templates ---
    if not Product.query.first():
        pbm = Product(name='Pasteurised Buffalo Milk', sku='PBM_500')
        pcm = Product(name='Sampoorna Cow Milk', sku='PCM_500')
        db.session.add_all([pbm, pcm])
        db.session.commit()
        click.echo('Created initial products.')

        # Associate plants with products (using the many-to-many relationship)
        all_plants = Plant.query.all()
        pbm.plants.extend(all_plants)
        pcm.plants.extend(all_plants)

        # Add templates
        pbm_templates = generate_default_templates(pbm, is_cow_milk=False)
        pcm_templates = generate_default_templates(pcm, is_cow_milk=True)
        
        db.session.add_all(pbm_templates)
        db.session.add_all(pcm_templates)
        db.session.commit()
        click.echo('Created initial product templates.')
        
    # --- 4. Populate Master Parameters ---
    if not ParameterMaster.query.first():
        click.echo("Populating default Master Parameters...")
        all_templates = ReportTemplate.query.all()
        master_params = {}
        for t in all_templates:
            master_params[t.parameter] = t.method
            
        for name, method in master_params.items():
            db.session.add(ParameterMaster(name=name, default_method=method))
        db.session.commit()
        click.echo('Created initial Master Parameters.')


    click.echo('Database initialization complete.')

def init_app(app):
    """Registers commands with the Flask app."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_user_command)