import os
import json
from datetime import datetime, timedelta
from copy import deepcopy


def time_left(deadline):
    return int((deadline - datetime.now()).total_seconds())


def min_sec(time):
    nb_of_minutes = time // 60
    nb_of_seconds = time % 60
    return nb_of_minutes, nb_of_seconds


def nice_time_display(time):
    nb_of_minutes, nb_of_seconds = min_sec(time)
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


def build_game_id(team_id, channel_id, organizer_id, trigger_id):
    return '{}&{}&{}&{}'.format(team_id, channel_id, organizer_id, trigger_id)


def build_slack_object_id(app_id, object_name, game_id):
    return '{}#{}#{}'.format(app_id, object_name, game_id)


def slack_object_id_to_game_id(slack_object_id):
    ids = slack_object_id.split('#')
    return ids[-1]


def get_game(slack_object_id, games):
    game_id = slack_object_id_to_game_id(slack_object_id)
    return games.get(game_id)


def exception_view(msg):
    res = deepcopy(exception_view_template)
    res['blocks'][0]['text']['text'] = msg
    return res


def get_channel_members(slack_client, channel_id):
    return slack_client.api_call(
        'conversations.members',
        channel=channel_id)['members']


def get_workspace_members(slack_client):
    return slack_client.api_call('users.list')['members']


def get_potential_guessers(slack_client, channel_id):
    res = set()
    channel_members = get_channel_members(slack_client, channel_id)
    workspace_members = get_workspace_members(slack_client)
    for m in workspace_members:
        c1 = m['id'] in channel_members
        c2 = not m['is_bot']
        c3 = not m['deleted']
        c4 = m['id'] != 'Truth'
        if c1 and c2 and c3 and c4:
            res.add(m['id'])
    return res


def open_view(slack_client, trigger_id, view):
    slack_client.api_call(
        'views.open',
        trigger_id=trigger_id,
        view=view)


def open_exception_view(slack_client, trigger_id, msg):
    open_view(slack_client, trigger_id, exception_view(msg))


def exception_view_response(msg):
    return {'response_action': 'update', 'view': exception_view(msg)}


def game_setup_view(game_id):
    res = deepcopy(game_setup_view_template)
    res['callback_id'] = game_id
    return res


def open_game_setup_view(slack_client, trigger_id, game_id):
    open_view(slack_client, trigger_id, game_setup_view(game_id))


def collect_game_setup(game_setup_view, debug):
    values = game_setup_view['state']['values']
    question = values['question']['question']['value']
    truth = values['truth']['truth']['value']
    if not debug:
        time_to_guess = int((values['time_to_guess']['time_to_guess']
                                   ['selected_option']['value']))*60
        time_to_vote = int((values['time_to_vote']['time_to_vote']
                                  ['selected_option']['value']))*60
    else:
        time_to_guess = 40
        time_to_vote = 35
    return question, truth, time_to_guess, time_to_vote


def game_id_to_ids(game_id):
    return game_id.split('&')


def game_id_to_channel_id(game_id):
    return game_id_to_ids(game_id)[1]


def game_id_to_organizer_id(game_id):
    return game_id_to_ids(game_id)[2]


def compute_deadline(time_left):
    return datetime.now() + timedelta(seconds=time_left)

