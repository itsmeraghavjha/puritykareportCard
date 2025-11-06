# # project/__init__.py
# # Application factory for creating the Flask app instance.

# import os
# from flask import Flask
# from flask_login import LoginManager
# from flask_sqlalchemy import SQLAlchemy
# from config import Config

# # Initialize extensions
# db = SQLAlchemy()
# login_manager = LoginManager()
# login_manager.login_view = 'admin.login'
# login_manager.login_message_category = 'info'

# def create_app(config_class=Config):
#     """
#     Creates and configures the Flask application.
#     """
#     app = Flask(__name__, instance_relative_config=True)
#     app.config.from_object(config_class)

#     # Ensure the instance folder exists
#     try:
#         os.makedirs(app.instance_path)
#     except OSError:
#         pass
        
#     # Ensure the upload folder exists
#     try:
#         os.makedirs(app.config['UPLOAD_FOLDER'])
#     except OSError:
#         pass

#     # Initialize extensions with the app
#     db.init_app(app)
#     login_manager.init_app(app)

#     from .models import User

#     @login_manager.user_loader
#     def load_user(user_id):
#         return User.query.get(int(user_id))

#     # Register blueprints for different parts of the app
#     from .routes import bp as main_blueprint
#     app.register_blueprint(main_blueprint)

#     # Register custom CLI commands
#     from . import commands
#     commands.init_app(app)

#     with app.app_context():
#         # You can create the database if it doesn't exist
#         # db.create_all() # It's better to use migrations
#         pass

#     return app



# project/__init__.py
# Application factory for creating the Flask app instance.

import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.qa_login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """
    Creates and configures the Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    # Ensure the upload folder exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints for different parts of the app
    from .routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    # Register custom CLI commands
    from . import commands
    commands.init_app(app)
    
    # --- Register the data population command ---
    from . import populate_db 
    populate_db.init_app(app)
    # --- End command registration ---

    with app.app_context():
        # db.create_all() # Using migrations instead
        pass

    return app