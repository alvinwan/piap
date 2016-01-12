from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import flask_login

# Parse configuration file
try:
    lines = filter(bool, open('config.cfg').read().splitlines())
    config = dict(map(lambda s: s.strip(), d.split(':')) for d in lines)
    settings = (config['username'],
        config['password'],
        config['server'],
        config['database'])
    secret_key = config['secret_key']
    debug = bool(config['debug'])
except FileNotFoundError:
    raise UserWarning('Configuration file not found. Rerun `make install` and \
    update the new queue.cfg accordingly.')
except KeyError:
    raise UserWarning('queue.cfg is missing critical information. All of the \
following must be present: username, password, server, database, secret_key, \
debug')

# Flask app
app = Flask(__name__)

# Configuration for mySQL database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@%s/%s' % settings
db = SQLAlchemy(app)

# Configuration for login sessions
app.secret_key = secret_key
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Configuration for app views
from .public.views import public
from .admin.views import admin

blueprints = (public, admin)
for blueprint in blueprints:
    print(' * Registering blueprint "%s"' % blueprint.name)
    app.register_blueprint(blueprint)
