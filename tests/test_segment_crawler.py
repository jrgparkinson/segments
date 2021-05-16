import src
from src.regions import RegionsData
from src.segment_crawler import (
    SegmentsData,
    split_box,
    retrieve_fastest_times,
    SegmentCrawler,
)
import os
from stravalib.model import SegmentExplorerResult
from stravalib.client import Client

import pytest

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def test_split_box():
    assert split_box([(0, 0), (2, 2)]) == [
        [(0, 0), (1.0, 1.0)],
        [(0, 1.0), (1.0, 2)],
        [(1.0, 1.0), (2, 2)],
        [(1.0, 0), (2, 1.0)],
    ]


def test_retrieve_fastest_times(mocker, segments_db):
    """
    Should do a single web look up for segment 1, and retrieve fastest athlete correctly
    """
    with open(os.path.join(DATA_DIR, "example_strava.html"), "r") as f:
        mock_html = f.read()
    mocker.patch("src.segment_crawler.get_html_from_url", return_value=mock_html)
    spy = mocker.spy(src.segment_crawler, "get_html_from_url")
    segments_db.data = [
        {
            "id": 1,
            "name": "Segment name",
            "distance": 1000.0,
            "avg_grade": 1.0,
            "climb": 10.0,
            "effort_count": 5,
            "start_latlng": 0.0,
            "end_latlng": 0.0,
        },
        {
            "id": 2,
            "name": "Segment 2",
            "distance": 1000.0,
            "avg_grade": 1.0,
            "climb": 10.0,
            "effort_count": 5,
            "start_latlng": 0.0,
            "end_latlng": 0.0,
            "fastest_athlete": "Jamie Parkinson",
            "fastest_time": "3:20",
        },
    ]

    retrieve_fastest_times(segments_db)

    assert spy.called_with("https://www.strava.com/segments/1")
    assert spy.call_count == 1

    assert segments_db.data[0]["fastest_athlete"] == "Miles Weatherseed"
    assert segments_db.data[0]["fastest_time"] == "4:05"


def test_retrieve_segments_none(mock_stravalib, segments_db, regions_db):
    mock_stravalib.patch("stravalib.client.Client.explore_segments", return_value=[])

    client = Client()
    bounds = [(0, 0), (2, 2)]

    crawler = SegmentCrawler(client, segments_db, regions_db, max_zoom=1)

    is_explored = crawler.retrieve_segments_recursively(bounds)

    assert is_explored
    assert not segments_db.data


def test_retrieve_segments_one_region(mock_stravalib, segments_db, regions_db):
    mock_stravalib.patch(
        "stravalib.client.Client.explore_segments",
        return_value=[SegmentExplorerResult(id=id) for id in range(5)],
    )
    client = Client()
    bounds = [(0, 0), (2, 2)]

    crawler = SegmentCrawler(client, segments_db, regions_db, max_zoom=1)

    is_explored = crawler.retrieve_segments_recursively(bounds)

    assert is_explored
    assert len(segments_db.data) == 5


def test_retrieve_segments_recursive(mock_stravalib, segments_db, regions_db):
    def segments_for_region(bounds, activity_type):
        segments_range = None
        if bounds == [(0, 0), (2, 2)]:
            segments_range = range(10)
        elif bounds == [(0, 0), (1.0, 1.0)]:
            segments_range = range(5)
        elif bounds == [(0, 1.0), (1.0, 2)]:
            segments_range = range(5, 10)
        elif bounds == [(1.0, 1.0), (2, 2)]:
            segments_range = range(10, 15)
        elif bounds == [(1.0, 0), (2, 1.0)]:
            segments_range = range(15, 20)

        return [SegmentExplorerResult(id=id) for id in segments_range]

    mock_stravalib.patch(
        "stravalib.client.Client.explore_segments", side_effect=segments_for_region
    )
    client = Client()
    bounds = [(0, 0), (2, 2)]

    crawler = SegmentCrawler(client, segments_db, regions_db, max_zoom=1)

    is_explored = crawler.retrieve_segments_recursively(bounds)

    assert is_explored
    assert len(segments_db.data) == 20


def test_not_explored(mock_stravalib, segments_db, regions_db):
    def segments_for_region(bounds, activity_type):
        segments_range = None
        if bounds == [(0, 0), (2, 2)]:
            segments_range = range(10)
        elif bounds == [(0, 0), (1.0, 1.0)]:
            segments_range = range(5)
        elif bounds == [(0, 1.0), (1.0, 2)]:
            segments_range = range(5, 10)
        elif bounds == [(1.0, 1.0), (2, 2)]:
            segments_range = range(10, 15)
        elif bounds == [(1.0, 0), (2, 1.0)]:
            segments_range = range(15, 25)

        return [SegmentExplorerResult(id=id) for id in segments_range]

    mock_stravalib.patch(
        "stravalib.client.Client.explore_segments", side_effect=segments_for_region
    )
    client = Client()
    bounds = [(0, 0), (2, 2)]

    crawler = SegmentCrawler(client, segments_db, regions_db, max_zoom=1)

    is_explored = crawler.retrieve_segments_recursively(bounds)

    assert not is_explored
    assert len(segments_db.data) == 25
