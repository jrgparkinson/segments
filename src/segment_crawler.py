import json
import sys
from urllib.request import urlopen
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
import matplotlib as mpl
import matplotlib.cm as cm
from stravalib.model import Segment

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
LOGGER.addHandler(handler)


class SegmentsData:

    FILENAME = "live_data/segments.json"

    def __init__(self, client=None, filename=None):
        if not filename:
            filename = self.FILENAME
        self.client = client
        self.filename = filename
        with open(self.filename, "r") as f:
            self.data = json.load(f)

    def get_segment(self, id):
        return next((seg for seg in self.data if "id" in seg and seg["id"] == id), None)

    def segment_exists(self, id) -> bool:
        return self.get_segment(id) is not None

    def add_segment(self, segment):
        self.data.append(segment)

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4, sort_keys=True)
            LOGGER.info(f"Saved {len(self.data)} segments to {self.filename}")

    def save_segments(self, retrieved_segments):
        for segment in retrieved_segments:
            if self.segment_exists(segment.id):
                continue
            seg_details = self.client.get_segment(segment.id)  # type: Segment
            key_details = {
                "id": seg_details.id,
                "name": seg_details.name,
                "distance": float(seg_details.distance),
                "avg_grade": float(seg_details.average_grade),
                "climb": float(seg_details.total_elevation_gain),
                "effort_count": int(seg_details.effort_count),
                "start_latlng": seg_details.start_latlng,
                "end_latlng": seg_details.end_latlng,
                "polyline": seg_details.map.polyline,
            }

            self.add_segment(key_details)

    def fill_polyline(self):
        to_fill = [
            seg for seg in self.data if "polyline" not in seg or seg["polyline"] is None
        ]
        n = 0
        LOGGER.info(f"Polyline to fill: {len(to_fill)}")
        for segment in to_fill:
            seg_details = self.client.get_segment(segment["id"])  # type: Segment
            segment["polyline"] = seg_details.map.polyline
            n += 1
            LOGGER.info(f"Process {n}/{len(to_fill)}")
            self.save()

    def display_segments(self, sort_by="fastest_pace"):

        for segment in self.data:

            segment["url"] = (
                f"https://www.strava.com/segments/{segment['id']}"
                if "id" in segment
                else "#"
            )

            if "fastest_time" in segment:
                if re.match(r"^\d+:\d+$", segment["fastest_time"]):
                    t = datetime.strptime(segment["fastest_time"], "%M:%S")
                elif re.match(r"^\d+:\d+:\d+$", segment["fastest_time"]):
                    t = datetime.strptime(segment["fastest_time"], "%H:%M:%S")
                elif re.match(r"^\d+s$", segment["fastest_time"]):
                    t = datetime.strptime(segment["fastest_time"][:-1], "%S")
                else:
                    raise Exception("Unknown time format: %s" % segment["fastest_time"])
                delta = timedelta(minutes=t.minute, seconds=t.second)
                segment["fastest_pace"] = round(
                    (delta.total_seconds() / 60.0) / (segment["distance"] / 1000.0), 1
                )
            else:
                segment["fastest_pace"] = float("NaN")

            segment["climb"] = round(segment["climb"], 2)

            norm = mpl.colors.Normalize(vmin=2.5, vmax=4.5)
            cmap = cm.viridis_r
            # cmap = cm.coolwarm
            m = cm.ScalarMappable(norm=norm, cmap=cmap)
            rgb = m.to_rgba(segment["fastest_pace"])
            segment["colour"] = mpl.colors.to_hex(rgb)

        self.data.sort(key=lambda x: x["fastest_pace"], reverse=True)
        return self.data


class SegmentCrawler:
    def __init__(self, client, segments_db, regions_db, max_zoom=5):
        self.client = client
        self.segments_db = segments_db
        self.regions_db = regions_db
        self.max_zoom = max_zoom

    def retrieve_segments_recursively(self, bounds, zoom_level=0):
        if zoom_level > self.max_zoom:
            return False

        # Check if this region has been fully explored
        if self.regions_db.is_explored(bounds):
            return True

        retrieved_segments = self.client.explore_segments(
            bounds, activity_type="running"
        )
        LOGGER.info(
            f"Retrieved {len(retrieved_segments)} segments on level {zoom_level}"
        )
        self.segments_db.save_segments(retrieved_segments)
        self.segments_db.save()

        if len(retrieved_segments) < 10:
            self.regions_db.set_explored(bounds, True)
            return True
        else:
            # more segments to retrieve
            new_boxes = split_box(bounds)
            is_explored = True
            for box in new_boxes:
                is_explored = is_explored and self.retrieve_segments_recursively(
                    box, zoom_level + 1
                )

            if is_explored:
                self.regions_db.set_explored(bounds, True)
                return True

        return False


def split_box(bounds):
    mid_point = (
        (bounds[0][0] + bounds[1][0]) / 2,
        (bounds[0][1] + bounds[1][1]) / 2,
    )
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
    return new_boxes


def get_html_from_url(url):
    with urlopen(url) as response:
        html = response.read().decode("utf8")
    return html


def retrieve_fastest_times(segments):
    segments_to_fill = [seg for seg in segments.data if "fastest_athlete" not in seg]
    count = 0
    for segment in segments_to_fill:

        url = "https://www.strava.com/segments/" + str(segment["id"])
        html = get_html_from_url(url)

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"class": "table-leaderboard"})
        leader = table.find("tbody").find("tr")
        rows = leader.find_all("td")

        name = rows[1].text.strip()
        time = rows[-1].text

        segment["fastest_athlete"] = name
        segment["fastest_time"] = time

        count += 1
        LOGGER.info(
            f"{segment['name']}: {name}, {time} ({count}/{len(segments_to_fill)})"
        )


if __name__ == "__main__":
    location = "oxford"
    segments = SegmentsData(filename=f"data/{location}/segments.json")
    retrieve_fastest_times(segments)
    segments.save()
