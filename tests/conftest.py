import pytest
from stravalib.model import SegmentExplorerResult, Segment
from stravalib.client import Client
import json
import os
import uuid
from src.regions import RegionsData
from src.segment_crawler import (
    SegmentsData,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@pytest.fixture
def segments_db():
    segments_file = os.path.join(DATA_DIR, f"segments_{uuid.uuid4()}.json")
    with open(segments_file, "w+") as f:
        json.dump([], f)
    try:
        yield SegmentsData(Client(), segments_file)

    finally:
        os.remove(segments_file)


@pytest.fixture
def regions_db():
    filename = os.path.join(DATA_DIR, f"regions_{uuid.uuid4()}.json")
    with open(filename, "w+") as f:
        json.dump([], f)
    try:
        yield RegionsData(filename)

    finally:
        os.remove(filename)


@pytest.fixture
def mock_stravalib(mocker):
    mocker.patch(
        "stravalib.client.Client.get_segment",
        side_effect=lambda x: Segment(
            id=x,
            name=f"Segment name",
            distance=1000,
            average_grade=1,
            total_elevation_gain=10,
            effort_count=0,
            start_latlng=(0.0, 0.0),
            end_latlng=(1.0, 0.0),
        ),
    )
    return mocker

