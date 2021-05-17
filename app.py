"""
Flask server for Track Splits app
"""
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template,
)
import os
import socket
import logging
import datetime
import coloredlogs
from flask.helpers import send_from_directory
from stravalib.client import Client
from src.segment_crawler import SegmentsData, SegmentCrawler, retrieve_fastest_times
from src.regions import RegionsData

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET")

STRAVA_CLIENT_ID = os.getenv("STRAVA_ID")
STRAVA_SECRET = os.getenv("STRAVA_SECRET")

LOGGER = logging.getLogger(__name__)
DEBUG_MODE = socket.gethostname() == "atmlxlap005"
LOGGING_LEVEL = "DEBUG" if DEBUG_MODE else "INFO"
coloredlogs.install(
    level=LOGGING_LEVEL,
    fmt="%(asctime)s %(hostname)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
)

# Disable stravalib warnings due to "Warning: Unable to set attribute elevation_profile on entity"
# with eveyr activity retrieved
logging.getLogger("stravalib").setLevel(logging.ERROR)


def get_data_path(location="oxford", filetype="segments"):
    return f"data/{location}/{filetype}.json"


def get_default_bounds(location):
    """Get first bounds from db for region"""
    bounds = None
    regions = RegionsData(get_data_path(location, filetype="regions"))
    if regions.data:
        bounds = regions.data[0]["bounds"]
    if not bounds:
        raise Exception(f"No bounds found for {location}")
    return bounds

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path,
                               'favicon.png', mimetype='image/vnd.microsoft.icon')

@app.route("/", methods=["GET"])
def index():
    """Home page"""
    _, authorize_url = get_client_or_authorize_url()

    location=request.args.get('offset')
    if not location:
        location = "oxford"

    segments = SegmentsData(None, get_data_path(location=location))
    return render_template(
        "index.html",
        authorize_url=authorize_url,
        segments=segments.display_segments(),
        location=location,
    )


@app.route("/retrieve/<string:location>", methods=["GET"])
def retrieve(location="oxford"):
    """Home page
    e.g.
    /retrieve/oxford?offset=0.02
    """
    client, authorize_url = get_client_or_authorize_url()

    # Oxford bounds
    # bottom left, top right
    bounds = None
    if bounds:
        p = bounds.split(",")
        bounds = [(p[0], p[1]), (p[2], p[3])]
    else:
        bounds = get_default_bounds(location)

    offset = float(request.args.get('offset'))
    if offset:
        for bound in bounds:
            bound[0] += offset
            bound[1] += offset

    LOGGER.info("Base coords: %s", bounds)

    segments = SegmentsData(client, get_data_path(location))
    regions = RegionsData(get_data_path(location, filetype="regions"))
    crawler = SegmentCrawler(client, segments, regions)

    if authorize_url is None:
        crawler.retrieve_segments_recursively(bounds)
    segments.save()
    regions.save()

    retrieve_fastest_times(segments)
    segments.save()

    return render_template(
        "index.html",
        authorize_url=authorize_url,
        segments=segments.display_segments(),
        location=location,
    )


@app.route("/authenticate")
def authenticate():
    """Authenticate user from Strava"""
    client = Client()
    code = request.args.get("code", None)

    try:
        token_response = client.exchange_code_for_token(
            client_id=STRAVA_CLIENT_ID, client_secret=STRAVA_SECRET, code=code
        )
        LOGGER.debug(token_response)
        session["strava_access_token"] = token_response["access_token"]
        session["strava_refresh_token"] = token_response["refresh_token"]
        session["strava_expires_at"] = token_response["expires_at"]

    except Exception as e:
        LOGGER.info(e)
        LOGGER.warning("Authentication failed")
        pass

    # return "Done"
    return redirect("/", code=302)


def get_client_or_authorize_url():
    """Get strava client, or authorization URL if not authenticated"""
    client = Client()
    authorize_url = None

    if "strava_refresh_token" in session.keys():
        client.refresh_token = session["strava_refresh_token"]

        LOGGER.debug(
            "{} / {} / {}".format(
                session["strava_access_token"],
                session["strava_refresh_token"],
                session["strava_expires_at"],
            )
        )

    if (
        "strava_access_token" in session.keys()
        and int(session["strava_expires_at"]) > datetime.datetime.now().timestamp()
    ):
        client.access_token = session["strava_access_token"]
        client.refresh_token = session["strava_refresh_token"]
        client.token_expires_at = session["strava_expires_at"]
    else:
        authorize_url = get_authorization_url()

    LOGGER.debug("Authorize URL: {}".format(authorize_url))
    return client, authorize_url


def get_authorization_url():
    client = Client()
    return client.authorization_url(
        client_id=STRAVA_CLIENT_ID,
        redirect_uri=url_for("authenticate", _external=True),
        scope=["activity:write", "activity:read_all"],
    )


if __name__ == "__main__":
    """
    Run web server with:
    python app.py
    """

    if DEBUG_MODE:
        # For local development
        app.run(debug=True, port=5001)
    else:
        LOGGER.info("Starting app on %s", socket.gethostname())
        # Threaded option to enable multiple instances for multiple user access support
        app.run(threaded=True, port=5000)
