from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
from .logger import logger
import functools
import flask_login
import os

# Extract information from environment.
get = lambda v, default: os.environ.get(v, default)

database_url = get('DATABASE_URL', 'mysql://root:root@localhost/queue')
url = urlparse(database_url)
config = {
    'NAME': url.path[1:],
    'USERNAME': url.username,
    'PASSWORD': url.password,
    'HOST': url.hostname,
    'PORT': url.port,
    'DATABASE': database_url.split('/')[3].split('?')[0],
    'SECRET_KEY': get('SECRET_KEY', 'dEf@u1t$eCRE+KEY'),
    'DEBUG': get('DEBUG', 'False'),
    'WHITELIST': get('WHITELIST', ''),
    'GOOGLECLIENTID': get('GOOGLECLIENTID', None)
}
try:
    lines = filter(bool, open('config.cfg').read().splitlines())
    for k, v in (map(lambda s: s.strip(), d.split(':')) for d in lines):
        if v:
            config[k.upper()] = v
except FileNotFoundError:
    print(' * Configuration file not found. Rerun `make install` and \
update the new config.cfg accordingly.')
    if not (config['HOST'] and config['USERNAME'] and config['DATABASE']):
        raise UserWarning('Environment variables do not supply database \
credentials, and configuration file is missing.')
except KeyError:
    raise UserWarning('config.cfg is missing critical information that is not \
found in the environment. All of the following must be present: username, \
password, server, database, secret_key, debug')

secret_key = config['SECRET_KEY']
debug = config['DEBUG'].lower() == 'true'
whitelist = config['WHITELIST'].split(',')
googleclientID = config['GOOGLECLIENTID']

logger.debug('Running in DEBUG mode.' if debug else
      'Running in PRODUCTION mode.')

logger.debug('Google Client ID: %s' % googleclientID if googleclientID else
      'No Google Client ID found.')

# Flask app
app = Flask(__name__)

# Configuration for mySQL database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE}'.format(**config)
db = SQLAlchemy(app)

# Configuration for login sessions
app.secret_key = secret_key
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Configuration for app views
from .public.views import public
from .dashboard.views import dashboard
from .group.views import group
from .event.views import event

blueprints = (public, dashboard, group, event)
for blueprint in blueprints:
    logger.debug('Registering blueprint "%s"' % blueprint.name)
    app.register_blueprint(blueprint)


def hook(f):
    pre = 'pre_%s' % f.__name__
    post = 'post_%s' % f.__name__
    @functools.wraps(f)
    def wrap(self, *args, **kwargs):
        pref, postf = getattr(self, pre, None), getattr(self, post, None)
        if callable(pref):
            pref(self, *args, **kwargs)
        rv = f(*args, **kwargs)
        if callable(postf):
            postf(self, *args, **kwargs)
        return rv
    return wrap
