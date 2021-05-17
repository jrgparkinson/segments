""" For managing regions of segments """
import json
import sys
import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
LOGGER.addHandler(handler)


class RegionsData:
    """Object to describe a region containing segments"""

    FILENAME = "live_data/regions.json"

    def __init__(self, filename=None):
        if not filename:
            filename = self.FILENAME
        self.filename = filename
        with open(self.filename, "r") as db_file:
            self.data = json.load(db_file)

    def set_explored(self, bounds, is_explored):
        """Set region as explored"""
        LOGGER.info("Set region explored (%s): %s", is_explored, str(bounds))
        self.get_region(bounds)["explored"] = True

    def is_explored(self, bounds):
        """Check if region is explored"""
        return self.get_region(bounds)["explored"]

    def init_region(self, bounds):
        """Initialise object for region"""
        region = {"bounds": bounds, "explored": False}
        self.data.append(region)
        return region

    def get_region(self, bounds):
        """Retrieve region from DB"""
        region = next(
            (
                region
                for region in self.data
                if "bounds" in region and region["bounds"] == bounds
            ),
            None,
        )

        if region is None:
            region = self.init_region(bounds)

        return region

    def save(self):
        """Save all regions to DB"""
        with open(self.filename, "w") as db_file:
            json.dump(self.data, db_file, indent=4, sort_keys=True)
            LOGGER.info(f"Saved {len(self.data)} regions to {self.filename}")

    def display(self):
        """Get regions to display"""
        return self.data
