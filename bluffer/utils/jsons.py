import os
import json


def get_json(dir_name, basename):
    utils_dir_path = os.path.dirname(__file__)
    package_dir_path = os.path.dirname(utils_dir_path)
    jsons_dir_path = os.path.join(package_dir_path, 'jsons')
    json_path = os.path.join(jsons_dir_path, dir_name, basename)
    with open(json_path) as f:
        return json.load(f)
