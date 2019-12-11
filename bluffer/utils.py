import os
import json
from datetime import datetime
from copy import deepcopy


def time_left(deadline):
    return int((deadline - datetime.now()).total_seconds())


def nice_time_display(time):
    nb_of_minutes = time // 60
    nb_of_seconds = time % 60
    nb_of_seconds_approx = nb_of_seconds - nb_of_seconds % 5
    return '{}min {}s'.format(nb_of_minutes, nb_of_seconds_approx)


def get_json(file_path, folder_name, basename):
    file_dir_path = os.path.abspath(os.path.dirname(file_path))
    modal_path = os.path.join(file_dir_path, 'jsons', folder_name, basename)
    with open(modal_path) as f:
        return json.load(f)


def get_view(file_path, basename):
    return get_json(file_path, 'views', basename)


def get_block(file_path, basename):
    return get_json(file_path, 'blocks', basename)


game_setup_view_template = get_view(__file__, 'game_setup.json')
guess_view_template = get_view(__file__, 'guess.json')
vote_view_template = get_view(__file__, 'vote.json')
exception_view_template = get_view(__file__, 'exception.json')

divider_block = get_block(__file__, 'divider.json')
text_block_template = get_block(__file__, 'text.json')
button_block_template = get_block(__file__, 'button.json')


def text_block(message):
    res = deepcopy(text_block_template)
    res['text']['text'] = message
    return res


def button_block(message):
    res = deepcopy(button_block_template)
    res['elements'][0]['text']['text'] = message
    return res


def decompose_object_id(object_id):
    ids = object_id.split('#')
    return {
        'object_name': ids[1],
        'team_id': ids[2],
        'channel_id': ids[3],
        'organizer_id': ids[4],
        'trigger_id': ids[5],
        'game_id': '#'.join(ids[2:])
    }


def get_game(object_id, games):
    ids = decompose_object_id(object_id)
    organizer_id = ids['organizer_id']
    game_id = ids['game_id']
    if organizer_id not in games or games[organizer_id].id != game_id:
        return None
    return games[organizer_id]


def exception_view(msg):
    res = deepcopy(exception_view_template)
    res['blocks'][0]['text']['text'] = msg
    return res


def get_channel_members(slack_client, channel_id):
    return slack_client.api_call(
        'conversations.members',
        channel=channel_id)['members']


def get_channel_non_bot_members(slack_client, channel_id):
    res = []
    for m in get_channel_members(slack_client, channel_id):
        if not slack_client.api_call(
                'users.info', user=m)['user']['is_bot']:
            res.append(m)
    return res


def open_exception_view(slack_client, trigger_id, msg):
    slack_client.api_call(
        'views.open',
        trigger_id=trigger_id,
        view=exception_view(msg))


def exception_view_response(msg):
    return {'response_action': 'update', 'view': exception_view(msg)}
