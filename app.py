"""
Flask server for Track Splits app
"""
from flask import Flask, flash, Response, request, redirect, url_for, session, render_template
import json
import re
import os
import socket
import logging
import datetime
from stravalib.client import Client

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET")

STRAVA_CLIENT_ID = os.getenv("STRAVA_ID")
STRAVA_SECRET = os.getenv("STRAVA_SECRET")

LOGGER = logging.getLogger(__name__)
DEBUG_MODE = socket.gethostname() == "atmlxlap005"
LOGGING_LEVEL = "DEBUG" if DEBUG_MODE else "INFO"

# Disable stravalib warnings due to "Warning: Unable to set attribute elevation_profile on entity"
# with eveyr activity retrieved
logging.getLogger("stravalib").setLevel(logging.ERROR)

@app.route('/', methods=['GET'])
def index():
    """ Home page """
    client, authorize_url = get_client_or_authorize_url()
    return render_template('index.html', authorize_url=authorize_url)


@app.route("/authenticate")
def authenticate():
    """ Authenticate user from Strava """
    client = Client()
    code = request.args.get("code", None)

    try:
        token_response = client.exchange_code_for_token(client_id=STRAVA_CLIENT_ID, client_secret=STRAVA_SECRET,
                                                        code=code)
        LOGGER.debug(token_response)
        session["strava_access_token"] = token_response['access_token']
        session["strava_refresh_token"] = token_response['refresh_token']
        session["strava_expires_at"] = token_response['expires_at']

    except Exception as e:
        LOGGER.info(e)
        LOGGER.warning("Authentication failed")
        pass

    # return "Done"
    return redirect("/", code=302)


def get_client_or_authorize_url():
    """ Get strava client, or authorization URL if not authenticated """
    client = Client()
    authorize_url = None

    if "strava_refresh_token" in session.keys():
        client.refresh_token = session['strava_refresh_token']

        LOGGER.debug("{} / {} / {}".format(session['strava_access_token'],
                                           session['strava_refresh_token'],
                                           session['strava_expires_at']))

    if 'strava_access_token' in session.keys() and int(
            session['strava_expires_at']) > datetime.datetime.now().timestamp():
        client.access_token = session['strava_access_token']
        client.refresh_token = session['strava_refresh_token']
        client.token_expires_at = session['strava_expires_at']
    else:
        authorize_url = get_authorization_url()

    LOGGER.debug("Authorize URL: {}".format(authorize_url))
    return client, authorize_url

def get_authorization_url():
    client = Client()
    return client.authorization_url(client_id=STRAVA_CLIENT_ID,
                                    redirect_uri=url_for('authenticate', _external=True),
                                    scope=["activity:write", "activity:read_all"])


if __name__ == "__main__":
    """
    Run web server with:
    python app.py
    """
    if DEBUG_MODE:
        # For local development
        app.run(debug=True)
    else:
        LOGGER.info("Starting app on %s", socket.gethostname())
        # Threaded option to enable multiple instances for multiple user access support
        app.run(threaded=True, port=5000)
