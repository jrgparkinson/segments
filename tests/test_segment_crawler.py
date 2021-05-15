from src.segment_crawler import SegmentsData
from stravalib.client import Client
import pytest

@pytest.fixture
def mock_stravalib(mocker):
    mocker.patch("stravalib.client.Client.explore_segments",
                  return_value=[])
    mocker.patch("stravalib.client.Client.get_segment",
                  return_value=[])
    return mocker

def test_nothing(mock_stravalib):
    client = Client()
    segs = SegmentsData(client)
    assert 1 == 1
