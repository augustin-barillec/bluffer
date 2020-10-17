import os
import time
import pytz
import json
import logging
from bluffer.game import Game

from copy import deepcopy
from flask import make_response
from google.cloud import pubsub_v1
from datetime import datetime
from bluffer.utils import *
from google.cloud import firestore

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level='INFO')
logger = logging.getLogger()

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

SECRET_PREFIX = 'secret_prefix'

dir_path = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(dir_path, 'project_id.txt')) as f:
    project_id = list(f)[0]


def build_game(game_id):
    return Game(
        game_id=game_id,
        secret_prefix=SECRET_PREFIX,
        project_id=project_id,
        publisher=publisher,
        db=db,
        logger=logger)


def slack_command(request):
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    game_id = ids.build_game_id(team_id, channel_id, organizer_id, trigger_id)
    game = build_game(game_id)

    game.get_team_dict()
    game.open_game_setup_view(trigger_id)

    return make_response('', 200)


def message_actions(request):
    message_action = json.loads(request.form['payload'])
    message_action_type = message_action['type']
    user_id = message_action['user']['id']
    trigger_id = message_action['trigger_id']

    if message_action_type == 'view_submission':
        view = message_action['view']
        view_callback_id = view['callback_id']

        game_id = ids.slack_object_id_to_game_id(view_callback_id)
        game = build_game(game_id)
        debug = game.get_team_dict()['debug']
        game_ref = game.get_game_ref()

        if view_callback_id.startswith(SECRET_PREFIX + '#game_setup_view'):
            question, truth, time_to_guess = views.collect_game_setup(view)

            if not debug[0]:
                time_to_vote = 600
            else:
                time_to_guess = debug[1]
                time_to_vote = debug[2]

            game_dict = {
                'question': question,
                'truth': truth,
                'time_to_guess': time_to_guess,
                'time_to_vote': time_to_vote,
            }

            game_ref.set(game_dict)

            game.trigger_pre_guess_stage()

            return make_response('', 200)

        game_dict = game.get_game_dict()
        if view_callback_id.startswith(SECRET_PREFIX + '#guess_view'):
            guess = views.collect_guess(view)
            guess_ts = datetime.now(pytz.UTC)
            game_dict['guessers'][user_id] = [guess_ts, guess]
            game_ref.set(game_dict, merge=True)
            game.update_guess_stage_lower()
            return make_response('', 200)

        if view_callback_id.startswith(SECRET_PREFIX + '#vote_view'):
            vote = views.collect_vote(view)
            vote_ts = datetime.now(pytz.UTC)
            game_dict['voters'][user_id] = [vote_ts, vote]
            game_ref.set(game_dict, merge=True)
            game.update_vote_stage_lower()
            return make_response('', 200)

    if message_action_type == 'block_actions':

        action_block_id = message_action['actions'][0]['block_id']
        game_id = ids.slack_object_id_to_game_id(action_block_id)
        game = build_game(game_id)
        game.get_team_dict()
        game.get_game_dict()

        if action_block_id.startswith(SECRET_PREFIX + '#guess_button_block'):
            game.open_guess_view(trigger_id)
            return make_response('', 200)

        if action_block_id.startswith(SECRET_PREFIX + '#vote_button_block'):
            game.open_vote_view(trigger_id, user_id)
            return make_response('', 200)


def pre_guess_stage(event, context):

    game_id = pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)
    game.get_team_dict()
    game.get_game_dict()
    game_dict = game.game_dict
    game_ref = game.get_game_ref()

    title_block = game.build_title_block()
    preparing_guess_stage_block = game.build_preparing_guess_stage_block()

    upper_blocks = blocks.u([title_block, preparing_guess_stage_block])
    lower_blocks = blocks.d([])

    upper_ts = game.post_message(upper_blocks)
    lower_ts = game.post_message(lower_blocks)

    potential_guessers = game.get_potential_guessers()

    guess_start_datetime = datetime.now(pytz.UTC)
    guess_deadline = timer.compute_deadline(
        guess_start_datetime, game_dict['time_to_guess'])

    game_dict['upper_ts'] = upper_ts
    game_dict['lower_ts'] = lower_ts
    game_dict['potential_guessers'] = potential_guessers
    game_dict['guessers'] = dict()
    game_dict['guess_start_datetime'] = guess_start_datetime
    game_dict['guess_deadline'] = guess_deadline
    game_ref.set(game_dict, merge=True)

    question_block = game.build_question_block()
    guess_button_block = game.build_guess_button_block()

    guess_timer_block = game.build_guess_timer_block()
    guessers_block = game.build_guessers_block()

    upper_blocks = blocks.u([title_block, question_block, guess_button_block])
    lower_blocks = blocks.d([guess_timer_block, guessers_block])

    game.update_upper(upper_blocks)
    game.update_lower(lower_blocks)

    game.trigger_guess_stage()
    return make_response('', 200)


def guess_stage(event, context):

    call_datetime = datetime.now(pytz.UTC)

    game_id = pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)
    game_ref = game.get_game_ref()
    game.get_team_dict()

    while True:
        game_dict = game.get_game_dict()

        time_left_to_guess = game.compute_time_left_to_guess()
        rpg = game.compute_remaining_potential_guessers()

        game.update_guess_stage_lower()

        if time_left_to_guess <= 0 or not rpg:
            game_dict['frozen_guessers'] = deepcopy(game_dict['guessers'])
            game_ref.set(game_dict, merge=True)
            game.trigger_pre_vote_stage()
            return make_response('', 200)

        if timer.d1_minus_d2(datetime.now(pytz.UTC), call_datetime) > 60:
            game.trigger_guess_stage()
            return make_response('', 200)

        time.sleep(5)


def pre_vote_stage(event, context):

    game_id = pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)
    game.get_team_dict()
    game.get_game_dict()
    game_dict = game.game_dict
    game_ref = game.get_game_ref()

    title_block = game.build_title_block()
    question_block = game.build_question_block()
    preparing_vote_stage_block = \
        game.build_preparing_vote_stage_block()

    upper_blocks = blocks.u([title_block, question_block,
                             preparing_vote_stage_block])
    lower_blocks = blocks.d([])
    game.update_upper(upper_blocks)
    game.update_lower(lower_blocks)

    vote_start_datetime = datetime.now(pytz.UTC)
    vote_deadline = timer.compute_deadline(
        vote_start_datetime, game_dict['time_to_vote'])

    game_dict['proposals'] = game.build_firestore_proposals()
    game_dict['potential_voters'] = game_dict['frozen_guessers']
    game_dict['voters'] = dict()
    game_dict['vote_start_datetime'] = vote_start_datetime
    game_dict['vote_deadline'] = vote_deadline
    game_ref.set(game_dict, merge=True)

    title_block = game.build_title_block()
    question_block = game.build_question_block()
    anonymous_proposals_block = game.build_anonymous_proposals_block()
    vote_button_block = game.build_vote_button_block()
    vote_timer_block = game.build_vote_timer_block()
    voters_block = game.build_voters_block()

    upper_blocks = blocks.u([title_block, question_block,
                             anonymous_proposals_block, vote_button_block])
    lower_blocks = blocks.d([vote_timer_block, voters_block])

    game.update_upper(upper_blocks)
    game.update_lower(lower_blocks)

    game.trigger_vote_stage()

    return make_response('', 200)


def vote_stage(event, context):
    call_datetime = datetime.now(pytz.UTC)

    game_id = pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)
    game_ref = game.get_game_ref()
    game.get_team_dict()

    while True:
        game_dict = game.get_game_dict()

        time_left_to_vote = game.compute_time_left_to_vote()
        rpv = game.compute_remaining_potential_voters()

        game.update_vote_stage_lower()

        if time_left_to_vote <= 0 or not rpv:
            game_dict['frozen_voters'] = deepcopy(game_dict['voters'])
            game_ref.set(game_dict, merge=True)
            game.trigger_result_stage()
            return make_response('', 200)

        if timer.d1_minus_d2(datetime.now(pytz.UTC), call_datetime) > 60:
            game.trigger_vote_stage()
            return make_response('', 200)

        time.sleep(5)


def result_stage(event, context):

    game_id = pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)
    game.get_team_dict()
    game.get_game_dict()

    title_block = game.build_title_block()
    question_block = game.build_question_block()
    computing_results_stage_block = \
        game.build_computing_results_stage_block()

    upper_blocks = blocks.u(
        [title_block, question_block, computing_results_stage_block])
    lower_blocks = blocks.d([])

    game.update_upper(upper_blocks)
    game.update_lower(lower_blocks)

    game.build_guesses()
    game.build_guessers()
    game.build_votes()
    game.build_voters()
    game.build_results()

    print('RESULTS: {}'.format(game.results))

    game.compute_max_score()
    game.compute_winners()
    signed_guesses_block = game.build_signed_guesses_block()
    conclusion_block = game.build_conclusion_block()

    upper_blocks = blocks.u(
        [title_block, question_block, signed_guesses_block, conclusion_block])

    game.update_upper(upper_blocks)

    return make_response('', 200)
