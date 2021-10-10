import json

def load_json(path):
    """Load json file and return data"""
    with open(path) as f:
        data = json.load(f)

    return data

def save_json(path, data):
    with open(path, "w") as outfile:
        json.dump(data, outfile)


