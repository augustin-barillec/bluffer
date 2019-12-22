import os
import json


def get_json(folder_name, basename):
    json_dir_path = os.path.join(__file__, '..', '..')
    json_path = os.path.join(json_dir_path, folder_name, basename)
    with open(json_path) as f:
        return json.load(f)
