from copy import deepcopy
from bluffer.utils.jsons import get_json
from bluffer.utils.ids import *


def get_view(basename):
    return get_json('views', basename)


exception_view_template = get_view('exception.json')
game_setup_view_template = get_view('game_setup.json')
guess_view_template = get_view('guess.json')
vote_view_template = get_view('vote.json')


def build_exception_view(msg):
    res = deepcopy(exception_view_template)
    res['blocks'][0]['text']['text'] = msg
    return res


def build_game_setup_view(secret_prefix, game_id):
    res = deepcopy(game_setup_view_template)
    id_ = build_slack_object_id(secret_prefix, 'game_setup_view', game_id)
    res['callback_id'] = id_
    return res


def build_exception_view_response(msg):
    exception_view = build_exception_view(msg)
    return {'response_action': 'update', 'view': exception_view}


def open_view(slack_client, trigger_id, view):
    slack_client.api_call(
        'views.open',
        trigger_id=trigger_id,
        view=view)


def open_exception_view(slack_client, trigger_id, msg):
    exception_view = build_exception_view(msg)
    open_view(slack_client, trigger_id, exception_view)


def open_game_setup_view(slack_client, trigger_id, secret_prefix, game_id):
    game_setup_view = build_game_setup_view(secret_prefix, game_id)
    open_view(slack_client, trigger_id, game_setup_view)


def collect_game_setup(game_setup_view, debug):
    values = game_setup_view['state']['values']
    question = values['question']['question']['value']
    truth = values['truth']['truth']['value']
    if not debug:
        time_to_guess = int((values['time_to_guess']['time_to_guess']
                                   ['selected_option']['value']))*60
    else:
        time_to_guess = 40
    return question, truth, time_to_guess


def collect_guess(guess_view):
    values = guess_view['state']['values']
    guess = values['guess']['guess']['value']
    return guess


def collect_vote(vote_view):
    values = vote_view['state']['values']
    vote = int(values['vote']['vote']['selected_option']['value'])
    return vote
