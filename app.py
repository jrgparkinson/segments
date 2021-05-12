"""
Flask server for Track Splits app
"""
from flask import (
    Flask,
    flash,
    Response,
    request,
    redirect,
    url_for,
    session,
    render_template,
)
import json
import re
import os
import socket
import logging
import datetime
import coloredlogs
from stravalib.client import Client
from src.segment_crawler import SegmentsData

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



def retrieve_segments_recursively(client, bounds, segments_db, zoom_level=0):
    if zoom_level > 2:
        return

    retrieved_segments = client.explore_segments(bounds, activity_type="running")
    LOGGER.info(
        f"Retrieve {len(retrieved_segments)} in bounding box on level {zoom_level}"
    )
    segments_db.save_segments(retrieved_segments)

    segments_db.save()

    if len(retrieved_segments) == 10:
        # more segments to retrieve
        # split area in 4
        mid_point = [
            (bounds[0][0] + bounds[1][0]) / 2,
            (bounds[0][1] + bounds[1][1]) / 2,
        ]
        new_boxes = [
            # bottom left quadrant
            [bounds[0], mid_point],
            # top left quadrant
            [(bounds[0][0], mid_point[1]), (mid_point[0], bounds[1][1])],
            # top right quadrant
            [mid_point, bounds[1]],
            # bottom right quadrant
            [(mid_point[0], bounds[0][1]), (bounds[1][0], mid_point[1])],
        ]

        for box in new_boxes:
            retrieve_segments_recursively(client, box, segments_db, zoom_level + 1)


@app.route("/", methods=["GET"])
def index():
    """ Home page """
    client, authorize_url = get_client_or_authorize_url()
    segments = SegmentsData()
    return render_template("index.html", authorize_url=authorize_url, segments=segments.display_segments())


@app.route("/retrieve", methods=["GET"])
def retrieve():
    """ Home page """
    client, authorize_url = get_client_or_authorize_url()

    # Oxford bounds
    # bottom left, top right
    bounds = [(51.723917, -1.301553), (51.792771, -1.185510)]

    # with open("data/segments.json", "r") as f:
    #     segments_db = json.load(f)

    segments = SegmentsData(client)

    # with open("data/regions.json", "r") as f:
    #     regions_db = json.load(f)

    if authorize_url is None:
        retrieve_segments_recursively(client, bounds, segments)
    segments.save()

    return render_template("index.html", authorize_url=authorize_url, segments=segments.display_segments())


@app.route("/authenticate")
def authenticate():
    """ Authenticate user from Strava """
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
    """ Get strava client, or authorization URL if not authenticated """
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
        app.run(debug=True)
    else:
        LOGGER.info("Starting app on %s", socket.gethostname())
        # Threaded option to enable multiple instances for multiple user access support
        app.run(threaded=True, port=5000)
