# app.py
# Main entry point for the Flask application.

import os
from project import create_app, db
from project.models import User, Product, ReportTemplate
from flask_migrate import Migrate
from datetime import datetime
from flask import Flask, request, redirect

# Create the Flask app using the factory pattern
app = create_app()
migrate = Migrate(app, db)

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


@app.before_request
def force_https():
    if request.url.startswith("http://"):
        return redirect(request.url.replace("http://", "https://", 1), code=301)

if __name__ == '__main__':

    cert_file = r"D:\certs\7db886ac63f4bfb8.pem"
    key_file = r"D:\certs\privateKey.key"

    # Run on HTTPS port 443
    app.run(host="0.0.0.0", port=8085, ssl_context=(cert_file, key_file), debug=False)


    # app.run(host='0.0.0.0', port=8085, debug=True)