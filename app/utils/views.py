from copy import deepcopy
from app.utils import jsons, blocks


def get_view(basename):
    return jsons.get_json('views', basename)


game_setup_view_template = get_view('game_setup.json')
guess_view_template = get_view('guess.json')
vote_view_template = get_view('vote.json')


def build_game_setup_view(id_):
    res = deepcopy(game_setup_view_template)
    res['callback_id'] = id_
    return res


def build_guess_view(id_, question):
    res = deepcopy(guess_view_template)
    res['callback_id'] = id_
    input_block = deepcopy(res['blocks'][0])
    question_block = blocks.build_text_block(question)
    res['blocks'] = [question_block, input_block]
    return res


def collect_game_setup(game_setup_view):
    values = game_setup_view['state']['values']
    question = values['question']['question']['value']
    truth = values['truth']['truth']['value']
    time_to_guess = int((values['time_to_guess']['time_to_guess']
                               ['selected_option']['value']))*60
    return question, truth, time_to_guess


def collect_guess(guess_view):
    values = guess_view['state']['values']
    guess = values['guess']['guess']['value']
    return guess


def collect_vote(vote_view):
    values = vote_view['state']['values']
    vote = int(values['vote']['vote']['selected_option']['value'])
    return vote
