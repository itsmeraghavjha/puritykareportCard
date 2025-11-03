# app.py
# Main entry point for the Flask application.

import os
from project import create_app, db
from project.models import User, Product, ReportTemplate
from flask_migrate import Migrate
from datetime import datetime
from flask_talisman import Talisman

# Create the Flask app using the factory pattern
app = create_app()
migrate = Migrate(app, db)

# Apply Flask-Talisman for HTTPS enforcement + security headers
talisman = Talisman(
    app,
    force_https=True,                        # Redirects to HTTPS if HTTP ever arrives
    strict_transport_security=True,          # Enables HSTS
    strict_transport_security_preload=True,  # Allows preload list inclusion
    strict_transport_security_max_age=31536000,  # 1 year in seconds
    content_security_policy=None             # Disable CSP if you don’t need it yet
)

@app.shell_context_processor
def make_shell_context():
    """
    Provides a shell context for the `flask shell` command,
    making it easier to test and debug models.
    """
    return {
        'db': db,
        'User': User,
        'Product': Product,
        'ReportTemplate': ReportTemplate
    }

@app.context_processor
def inject_current_year():
    """
    Makes the current year available in all Jinja templates
    as `current_year`.
    """
    return {'current_year': datetime.utcnow().year}


# if __name__ == '__main__':
#     cert_file = r"D:\certs\7db886ac63f4bfb8.pem"
#     key_file = r"D:\certs\privateKey.key"

#     # Run with HTTPS on port 8085
#     app.run(host="0.0.0.0", port=8085, ssl_context=(cert_file, key_file), debug=False)
