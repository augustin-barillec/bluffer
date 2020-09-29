from copy import deepcopy
from bluffer.utils.jsons import get_json
from bluffer.utils.ids import user_display
from bluffer.utils.timer import build_time_display


def get_block(basename):
    return get_json('blocks', basename)


divider_block = get_block('divider.json')
text_block_template = get_block('text.json')
button_block_template = get_block('button.json')
image_block_template = get_block('image.json')


def build_text_block(msg):
    res = deepcopy(text_block_template)
    res['text']['text'] = msg
    return res


def build_button_block(msg, id_):
    res = deepcopy(button_block_template)
    res['elements'][0]['text']['text'] = msg
    res['block_id'] = id_
    return res


def build_image_block(url, alt_text):
    res = deepcopy(image_block_template)
    res['image_url'] = url
    res['alt_text'] = alt_text
    return res


def build_title_block(organizer_id):
    msg = 'Game set up by {}!'.format(user_display(organizer_id))
    return build_text_block(msg)


def build_pre_guess_stage_block():
    return build_text_block('Preparing guess stage...')


def build_pre_vote_stage_block():
    return build_text_block('Preparing vote stage...')


def build_pre_results_stage_block():
    return build_text_block('Computing results :drum_with_drumsticks:')


def build_guess_button_block(id_):
    return build_button_block('Your guess', id_)


def build_vote_button_block(id_):
    return build_button_block('Your vote', id_)


def build_timer_block(time_left, kind):
    assert kind in ('guess', 'vote')
    time_display = build_time_display(time_left)
    msg = 'Time left to {}: {}'.format(kind, time_display)
    return build_text_block(msg)


def build_guess_timer_block(time_left):
    return build_timer_block(time_left, 'guess')


def build_vote_timer_block(time_left):
    return build_timer_block(time_left, 'vote')
