from flask import Blueprint, request, redirect, session
from .forms import *
from piipod import app, login_manager, logger, googleclientID
from piipod.models import User, Group
from piipod.views import anonymous_required, render, url_for, current_url
from urllib.parse import urlparse
import flask_login
from sqlalchemy import desc
from oauth2client import client, crypt
from apiclient.discovery import build
from apiclient import discovery
import httplib2

# Google API service object for Google Plus
service = build('plus', 'v1')

public = Blueprint('public', __name__)

##########
# PUBLIC #
##########

@public.route('/')
def home():
    """Home page"""
    return render('index.html')

##################
# LOGIN/REGISTER #
##################

@public.route('/login', methods=['POST', 'GET'])
def login(home=None, login=None):
    """
    Login using Google authentication

    :param str home: URL for queue homepage
    :param str login: URL for queue login page
    """
    try:
        flow = client.flow_from_clientsecrets(
            'client_secrets.json',
            scope='openid profile email https://www.googleapis.com/auth/calendar.readonly',
            redirect_uri=login or url_for('public.login', _external=True))
        if 'code' not in request.args:
            auth_uri = flow.step1_get_authorize_url()
            return redirect(auth_uri+'&prompt=select_account')
        credentials = flow.step2_exchange(request.args.get('code'))
        session['credentials'] = credentials.to_json()

        http = credentials.authorize(httplib2.Http())
        person = service.people().get(userId='me').execute(http=http)

        user = User.query.filter_by(email=person['emails'][0]['value']).first()
        if not user:
            user = User(
                name=person['displayName'],
                email=person['emails'][0]['value'],
                google_id=person['id'],
                image_url=person['image']['url']
            ).save()
        else:
            user.update(
                google_id=person['id'],
                image_url=person['image']['url']).save()
        flask_login.login_user(user)
        return redirect(home or url_for('public.home'))
    except client.FlowExchangeError:
        return redirect(login or url_for('public.login'))

######################
# SESSION UTILIITIES #
######################

@login_manager.user_loader
def user_loader(id):
    """Load user by id"""
    return User.query.get(id)

@login_manager.request_loader
def request_loader(request):
    """Loads user from Flask Request object"""
    user = User.query.get(int(request.form.get('id') or 0))
    if not user:
        return
    user.is_authenticated = user.password == request.form['password']
    return user

@public.route('/logout')
def logout(home=None):
    """
    Logs out current session and redirects to home

    :param str home: URL to redirect to after logout success
    """
    flask_login.logout_user()
    return redirect(request.args.get('redirect',
        home or url_for('public.home')))

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('public.login'))

##################
# ERROR HANDLERS #
##################

@app.errorhandler(404)
def not_found(error):
    return render('error.html',
        title='404. Oops.',
        code=404,
        message='Oops. This page doesn\'t exist!',
        url='/',
        action='Return to homepage?'), 404


@app.errorhandler(500)
def not_found(error):
    return render('error.html',
        title='500. Hurr.',
        code=500,
        message='Sorry. Here is the error: <br><code>%s</code><br> Please file an issue on the <a href="https://github.com/alvinwan/piipod/issues">Github issues page</a>, with the above code if it has not already been submitted.' % str(error)), 500
