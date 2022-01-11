"""
Utility functions for handling JSON files
"""

import json


def load_json(path):
    """Load json file from given path and return data"""
    with open(path) as f:
        data = json.load(f)

    return data

def save_json(path: str, data):
    """Save json file in given path"""
    with open(path, "w") as outfile:
        json.dump(data, outfile)

