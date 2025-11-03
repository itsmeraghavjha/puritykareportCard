from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='qa') # 'qa' or 'superadmin'
    plant_name = db.Column(db.String(100), nullable=False)
    signature_filename = db.Column(db.String(200), nullable=True)
    reports = db.relationship('QualityReport', backref='creator', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    templates = db.relationship('ReportTemplate', backref='product', lazy=True, cascade="all, delete-orphan")

class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class ReportTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    parameter = db.Column(db.String(200), nullable=False)
    specification = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, nullable=False)

class QualityReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    batch_code = db.Column(db.String(50), nullable=False)
    # BEST PRACTICE: Add the new field to store machine codes.
    # It is nullable to ensure old reports without this data remain valid.
    machine_codes = db.Column(db.String(500), nullable=True)
    expiry_date = db.Column(db.Date, nullable=False)
    plant_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product')
    results = db.relationship('ReportResult', backref='report', lazy='dynamic', cascade="all, delete-orphan")

class ReportResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('quality_report.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('report_template.id'), nullable=False)
    result_value = db.Column(db.String(100), nullable=False)
    template = db.relationship('ReportTemplate')