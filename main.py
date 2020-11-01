import os
import time
import pytz
import json
import yaml
import logging

from copy import deepcopy
from datetime import datetime
from flask import make_response
from google.cloud import pubsub_v1, firestore, storage

from app.game import Game
from app import utils

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level='INFO')
logger = logging.getLogger()

dir_path = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(dir_path, 'conf.yaml')) as f:
    conf = yaml.safe_load(f)

secret_prefix = conf['secret_prefix']
project_id = conf['project_id']
bucket_name = conf['bucket_name']
local_dir_path = conf['local_dir_path']

publisher = pubsub_v1.PublisherClient()
db = firestore.Client(project=project_id)
storage_client = storage.Client(project=project_id)
bucket = storage_client.bucket(bucket_name)


def build_game(game_id, fetch_game_data=True):
    return Game(
        game_id=game_id,
        secret_prefix=secret_prefix,
        project_id=project_id,
        publisher=publisher,
        db=db,
        bucket=bucket,
        logger=logger,
        local_dir_path=local_dir_path,
        fetch_game_data=fetch_game_data)


def slack_command(request):
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    game_creation_ts = utils.time.build_compact_format(utils.time.get_now())

    game_id = utils.ids.build_game_id(
        game_creation_ts, team_id, channel_id, organizer_id, trigger_id)
    game = build_game(game_id, fetch_game_data=False)

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

        game_id = utils.ids.slack_object_id_to_game_id(view_callback_id)

        if view_callback_id.startswith(secret_prefix + '#game_setup_view'):
            question, truth, time_to_guess = utils.views.collect_game_setup(
                view)
            game = build_game(game_id, fetch_game_data=False)
            debug = game.team_dict['debug']

            if not debug[0]:
                time_to_vote = 600
            else:
                time_to_guess = debug[1]
                time_to_vote = debug[2]

            game.game_dict = {
                'question': question,
                'truth': truth,
                'time_to_guess': time_to_guess,
                'time_to_vote': time_to_vote,
            }

            game.set_game_dict()

            game.trigger_pre_guess_stage()

            return make_response('', 200)

        game = build_game(game_id)

        if view_callback_id.startswith(secret_prefix + '#guess_view'):
            guess = utils.views.collect_guess(view)
            guess_start = utils.time.get_now()
            game.game_dict['guessers'][user_id] = [guess_start, guess]
            game.set_game_dict(merge=True)
            game.update_guess_stage_lower()
            return make_response('', 200)

        if view_callback_id.startswith(secret_prefix + '#vote_view'):
            vote = utils.views.collect_vote(view)
            vote_start = utils.time.get_now()
            game.game_dict['voters'][user_id] = [vote_start, vote]
            game.set_game_dict(merge=True)
            game.update_vote_stage_lower()
            return make_response('', 200)

    if message_action_type == 'block_actions':

        action_block_id = message_action['actions'][0]['block_id']
        game_id = utils.ids.slack_object_id_to_game_id(action_block_id)
        game = build_game(game_id)

        if action_block_id.startswith(secret_prefix + '#guess_button_block'):
            game.open_guess_view(trigger_id)
            return make_response('', 200)

        if action_block_id.startswith(secret_prefix + '#vote_button_block'):
            game.open_vote_view(trigger_id, user_id)
            return make_response('', 200)


def pre_guess_stage(event, context):

    game_id = utils.pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)

    upper_ts, lower_ts = game.post_pre_guess_stage()

    potential_guessers = game.get_potential_guessers()

    guess_start = utils.time.get_now()
    guess_deadline = utils.time.compute_deadline(
        guess_start, game.time_to_guess)

    game.game_dict['upper_ts'] = upper_ts
    game.game_dict['lower_ts'] = lower_ts
    game.game_dict['potential_guessers'] = potential_guessers
    game.game_dict['guessers'] = dict()
    game.game_dict['guess_start'] = guess_start
    game.game_dict['guess_deadline'] = guess_deadline
    game.set_game_dict(merge=True)

    game.diffuse_game_dict()

    game.update_guess_stage()

    game.trigger_guess_stage()
    return make_response('', 200)


def guess_stage(event, context):

    call_datetime = datetime.now(pytz.UTC)

    game_id = utils.pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id, fetch_game_data=False)

    while True:
        game.game_dict = game.get_game_dict()
        game.diffuse_game_dict()

        game.update_guess_stage_lower()

        time_left_to_guess = game.compute_time_left_to_guess()
        rpg = game.compute_remaining_potential_guessers()

        if time_left_to_guess <= 0 or not rpg:
            game_dict = game.game_dict
            game_dict['frozen_guessers'] = deepcopy(game_dict['guessers'])
            game.set_game_dict(merge=True)
            game.trigger_pre_vote_stage()
            return make_response('', 200)

        if utils.time.datetime1_minus_datetime2(
                utils.time.get_now(), call_datetime) > 60:
            game.trigger_guess_stage()
            return make_response('', 200)

        time.sleep(5)


def pre_vote_stage(event, context):

    game_id = utils.pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)

    game.update_pre_vote_stage()

    vote_start = utils.time.get_now()
    vote_deadline = utils.time.compute_deadline(
        vote_start, game.time_to_vote)

    game.indexed_signed_proposals = game.build_indexed_signed_proposals()

    game.game_dict['firestore_indexed_signed_proposals'] = \
        game.to_firestore_indexed_signed_proposals(
            game.indexed_signed_proposals)
    game.game_dict['potential_voters'] = game.frozen_guessers
    game.game_dict['voters'] = dict()
    game.game_dict['vote_start'] = vote_start
    game.game_dict['vote_deadline'] = vote_deadline
    game.set_game_dict(merge=True)

    game.diffuse_game_dict()

    game.update_vote_stage()

    game.trigger_vote_stage()
    return make_response('', 200)


def vote_stage(event, context):
    call_datetime = datetime.now(pytz.UTC)

    game_id = utils.pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id, fetch_game_data=False)

    while True:
        game.game_dict = game.get_game_dict()
        game.diffuse_game_dict()

        game.update_vote_stage_lower()

        time_left_to_vote = game.compute_time_left_to_vote()
        rpv = game.compute_remaining_potential_voters()

        if time_left_to_vote <= 0 or not rpv:
            game_dict = game.game_dict
            game_dict['frozen_voters'] = deepcopy(game_dict['voters'])
            game.set_game_dict(merge=True)
            game.trigger_pre_result_stage()
            return make_response('', 200)

        if utils.time.datetime1_minus_datetime2(datetime.now(pytz.UTC),
                                                call_datetime) > 60:
            game.trigger_vote_stage()
            return make_response('', 200)

        time.sleep(5)


def pre_result_stage(event, context):

    game_id = utils.pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)

    game.update_pre_result_stage()

    game.truth_index = game.compute_truth_index()
    game.results = game.build_results()
    game.max_score = game.compute_max_score()
    game.winners = game.compute_winners()
    game.graph = game.build_graph()
    game.draw_graph()
    game.graph_local_path = game.build_graph_local_path()
    game.graph_url = game.upload_graph_to_gs()

    game.update_result_stage()

    game.trigger_result_stage()

    return make_response('', 200)


def result_stage(event, context):

    game_id = utils.pubsub.event_data_to_game_id(event['data'])

    game = build_game(game_id)

    debug = game.team_dict['debug']

    if not debug[0]:
        time.sleep(480)
        game.delete()

    return make_response('', 200)
