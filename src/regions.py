import json
import sys
import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
LOGGER.addHandler(handler)


class RegionsData:

    FILENAME = "live_data/regions.json"

    def __init__(self):
        with open(self.FILENAME, "r") as f:
            self.data = json.load(f)

    def set_explored(self, bounds, is_explored):
        LOGGER.info("Set region explored (%s): %s", is_explored, str(bounds))
        self.get_region(bounds)["explored"] = True

    def is_explored(self, bounds):
        return self.get_region(bounds)["explored"]

    def init_region(self, bounds):
        region = {"bounds": bounds, "explored": False}
        self.data.append(region)
        return region

    def get_region(self, bounds):
        region = next((region for region in self.data if region["bounds"] == bounds), None)

        if region is None:
            region = self.init_region(bounds)

        return region

    def save(self):
        with open(self.FILENAME, "w") as f:
            json.dump(self.data, f)
            LOGGER.info(f"Saved {len(self.data)} regions to {self.FILENAME}")

    
    def display(self):
        return self.data