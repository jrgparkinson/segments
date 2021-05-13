import json
import sys
from urllib.request import urlopen
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
import matplotlib as mpl
import matplotlib.cm as cm



LOGGER = logging.getLogger(__name__)

LOGGER.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
LOGGER.addHandler(handler)

class SegmentsData:

    FILENAME = "live_data/segments.json"

    def __init__(self, client=None):
        self.client = client
        with open(self.FILENAME, "r") as f:
            self.data = json.load(f)

    def get_segment(self, id):
        return next((seg for seg in self.data if seg["id"] == id), None)

    def segment_exists(self, id) -> bool:
        return self.get_segment(id) is not None

    def add_segment(self, segment):
        self.data.append(segment)

    def save(self):
        with open(self.FILENAME, "w") as f:
            json.dump(self.data, f)
            LOGGER.info(f"Saved {len(self.data)} segments to {self.FILENAME}")

    def save_segments(self, retrieved_segments):
        for segment in retrieved_segments:
            if self.segment_exists(segment.id):
                continue

            seg_details = self.client.get_segment(segment.id)
            # LOGGER.info(seg_details)

            key_details = {
                "id": seg_details.id,
                "name": seg_details.name,
                "distance": float(seg_details.distance),
                "avg_grade": float(seg_details.average_grade),
                "climb": float(seg_details.total_elevation_gain),
                "effort_count": int(seg_details.effort_count),
                "start_latlng": seg_details.start_latlng,
                "end_latlng": seg_details.end_latlng,
            }

            self.add_segment(key_details)

    def display_segments(self, sort_by="fastest_pace"):

        for segment in self.data:

            segment["url"] = f"https://www.strava.com/segments/{segment['id']}"

            if "fastest_time" in segment:
                if re.match(r"^\d+:\d+$", segment["fastest_time"]):
                    t = datetime.strptime(segment["fastest_time"],"%M:%S")
                elif re.match(r"^\d+:\d+:\d+$", segment["fastest_time"]):
                    t = datetime.strptime(segment["fastest_time"],"%H:%M:%S")
                elif re.match(r"^\d+s$", segment["fastest_time"]):
                    t = datetime.strptime(segment["fastest_time"][:-1],"%S")
                else:
                    raise Exception("Unknown time format: %s" % segment["fastest_time"])
                delta = timedelta(minutes=t.minute, seconds=t.second)
                segment["fastest_pace"] = round((delta.total_seconds()/60.0)/(segment["distance"]/1000.0), 1)
            else:
                segment["fastest_pace"] = float("NaN")

            segment["climb"] = round(segment["climb"], 2)

            norm = mpl.colors.Normalize(vmin=2.5, vmax=4.5)
            cmap = cm.viridis_r
            # cmap = cm.coolwarm
            m = cm.ScalarMappable(norm=norm, cmap=cmap)
            rgb = m.to_rgba(segment["fastest_pace"])
            segment["colour"] = mpl.colors.to_hex(rgb)

        self.data.sort(key=lambda x:x["fastest_pace"], reverse=True)
        return self.data



def retrieve_segments_recursively(client, bounds, segments_db, regions, zoom_level=0):
    if zoom_level > 8:
        return False

    # Check if this region has been fully explored
    if regions.is_explored(bounds):
        return True

    retrieved_segments = client.explore_segments(bounds, activity_type="running")
    LOGGER.info(
        f"Retrieve {len(retrieved_segments)} in bounding box on level {zoom_level}"
    )
    segments_db.save_segments(retrieved_segments)

    segments_db.save()

    if len(retrieved_segments) < 10:
        regions.set_explored(bounds, True)
        return True
    else:
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

        is_explored = True
        for box in new_boxes:
            is_explored = is_explored and retrieve_segments_recursively(client, box, segments_db, regions, zoom_level + 1)

        if is_explored:
            regions.set_explored(bounds, True)
            return True

    return False


if __name__ == "__main__":

    segments = SegmentsData()

    for segment in segments.data:

        if "fastest_athlete" not in segment:

            url = "https://www.strava.com/segments/" + str(segment["id"])
            with urlopen(url) as response:
                html = response.read().decode("utf8")
            # with open("src/example_strava.html") as f:
            #     html = f.read()
            # print(html)
            soup = BeautifulSoup(html, 'html.parser')

            table = soup.find("table", {"class":"table-leaderboard"})

            leader = table.find("tbody").find("tr")

            rows = leader.find_all("td")

            name = rows[1].text
            time = rows[-1].text

            LOGGER.info(f"{segment['name']}: {name}, {time}")
            
            segment["fastest_athlete"] = name
            segment["fastest_time"] = time

    segments.save()