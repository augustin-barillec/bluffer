from copy import deepcopy
from app.utils.jsons import get_json
from app.utils.time import build_time_display


def get_block(basename):
    return get_json('blocks', basename)


divider_block = get_block('divider.json')
text_block_template = get_block('text.json')
button_block_template = get_block('button.json')
image_block_template = get_block('image.json')


def u(blocks):
    return [divider_block] + blocks


def d(blocks):
    return blocks + [divider_block]


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


def build_timer_block(time_left, kind):
    assert kind in ('guess', 'vote')
    time_display = build_time_display(time_left)
    msg = 'Time left to {}: {}'.format(kind, time_display)
    return build_text_block(msg)


def build_guess_timer_block(time_left):
    return build_timer_block(time_left, 'guess')


def build_vote_timer_block(time_left):
    return build_timer_block(time_left, 'vote')
