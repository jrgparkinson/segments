#!/usr/bin/env /home/parkinsonjl/code/strava-segments/.venv2/bin/python
""" Script to retrieve fastest times for segments

Use --r option to force reparsing all segments, otherwise 
just retrieve times for those segments which don't currently have them
./run.py oxford --r
"""
import argparse
from src.segment_crawler import SegmentsData, retrieve_fastest_times

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('location', type=str, nargs="?", default="oxford", help='Location')
    parser.add_argument('--r', default=False, dest='reparse', action='store_true',
                        help='To reparse all segments')
    args = parser.parse_args()

    segments = SegmentsData(filename=f"data/{args.location}/segments.json")
    retrieve_fastest_times(segments, args.reparse)
    segments.save()
