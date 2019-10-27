import os
import json


def get_bluffer_channel_id(slack_client):
    private_channels = slack_client.api_call(
        "users.conversations",
        types='public_channel, private_channel')['channels']
    res = None
    for c in private_channels:
        if 'name' in c and 'bluffer' in c['name']:
            res = c['id']
        break
    return res


def get_json(file_path, folder_name, basename):
    file_dir_path = os.path.abspath(os.path.dirname(file_path))
    modal_path = os.path.join(file_dir_path, 'jsons', folder_name, basename)
    with open(modal_path) as f:
        return json.load(f)


def get_modal(file_path, basename):
    return get_json(file_path, 'modals', basename)


def get_message(file_path, basename):
    return get_json(file_path, 'messages', basename)
