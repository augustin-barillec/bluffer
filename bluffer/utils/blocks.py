from copy import deepcopy
from bluffer.utils.jsons import get_json


def get_block(basename):
    return get_json('blocks', basename)


divider_block = get_block('divider.json')
text_block_template = get_block('text.json')
button_block_template = get_block('button.json')


def build_text_block(msg):
    res = deepcopy(text_block_template)
    res['text']['text'] = msg
    return res


def build_button_block(msg, id_):
    res = deepcopy(button_block_template)
    res['elements'][0]['text']['text'] = msg
    res['block_id'] = id_
    return res


def build_title_block(organizer_id):
    msg = 'Game set up by <@{}>!'.format(organizer_id)
    return build_text_block(msg)


def build_pre_guess_stage_block():
    return build_text_block('Preparing guessing stage...')


def build_pre_vote_stage_block():
    return build_text_block('Preparing voting stage...')


def build_pre_results_stage_block():
    return build_text_block('Computing results :drum_with_drumsticks:')
