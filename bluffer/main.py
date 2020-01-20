import time
import threading
import argparse
import json
import yaml
from flask import Flask, Response, request, make_response
from slackclient import SlackClient
from google.oauth2 import service_account
from google.cloud import storage
from apiclient import discovery
from bluffer.game import Game
from bluffer.utils import *


parser = argparse.ArgumentParser()
parser.add_argument('conf_path')
args = parser.parse_args()

with open(args.conf_path) as f:
    conf = yaml.safe_load(f)

BOT_TOKEN = conf['bot_token']
GOOGLE_CREDENTIALS_PATH = conf['google_credentials_path']
SECRET_PREFIX = conf['secret_prefix']
PORT = conf['port']
BUCKET_NAME = conf['bucket_name']
BUCKET_DIR_NAME = conf['bucket_dir_name']
DRIVE_DIR_ID = conf['drive_dir_id']
LOCAL_DIR_PATH = conf['local_dir_path']
DEBUG = conf['debug']
DEBUG_TIME_TO_GUESS = conf['debug_time_to_guess']
DEBUG_TIME_TO_VOTE = conf['debug_time_to_vote']


slack_client = SlackClient(token=BOT_TOKEN)
google_credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_CREDENTIALS_PATH)
storage_client = storage.Client(credentials=google_credentials)
bucket = storage_client.bucket(BUCKET_NAME)
drive_service = discovery.build('drive', 'v3', credentials=google_credentials)

app = Flask(__name__)

GAMES = dict()


def erase_dead_games():
    while True:
        dead_game_ids = []
        for game_id in GAMES:
            if GAMES[game_id].is_over:
                dead_game_ids.append(game_id)
        for game_id in dead_game_ids:
            GAMES[game_id].thread_update_regularly.join()
            del GAMES[game_id]
        time.sleep(1)


@app.route('/slack/command', methods=['POST'])
def command():
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    if len(GAMES) > 2:
        msg = ('There are too many (more than 2) games '
               'running!')
        views.open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    app_conversations = slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']
    if channel_id not in [c['id'] for c in app_conversations]:
        msg = 'Please invite me first to this conversation!'
        views.open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    if organizer_id in [GAMES[id_].organizer_id for id_ in GAMES
                        if not GAMES[id_].is_over]:
        msg = ('You are the organizer of a game which is sill running. '
               'You can only have one game running at a time.')
        views.open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    game_id = ids.build_game_id(team_id, channel_id, organizer_id, trigger_id)
    views.open_game_setup_view(slack_client, trigger_id,
                               SECRET_PREFIX, game_id)

    return make_response('', 200)


@app.route('/slack/message_actions', methods=['POST'])
def message_actions():
    message_action = json.loads(request.form['payload'])
    message_action_type = message_action['type']
    user_id = message_action['user']['id']
    trigger_id = message_action['trigger_id']

    if message_action_type not in ('block_actions', 'view_submission'):
        return make_response('', 200)

    if message_action_type == 'view_submission':
        view = message_action['view']
        view_callback_id = view['callback_id']

        if not view_callback_id.startswith(SECRET_PREFIX):
            return make_response('', 200)

        game_id = ids.slack_object_id_to_game_id(view_callback_id)

        if view_callback_id.startswith(SECRET_PREFIX + '#game_setup_view'):
            question, truth, time_to_guess = \
                views.collect_game_setup(view)
            if not DEBUG:
                time_to_vote = 600
                bucket_dir_name = BUCKET_DIR_NAME
            else:
                time_to_guess = DEBUG_TIME_TO_GUESS
                time_to_vote = DEBUG_TIME_TO_VOTE
                bucket_dir_name = 'test_' + BUCKET_DIR_NAME
            GAMES[game_id] = Game(
                question, truth,
                time_to_guess, time_to_vote,
                game_id, SECRET_PREFIX,
                bucket_dir_name,
                DRIVE_DIR_ID,
                LOCAL_DIR_PATH,
                slack_client,
                bucket,
                drive_service)
            return make_response('', 200)

        game = GAMES.get(game_id)
        if game is None:
            msg = 'This game is dead!'
            exception_view_response = views.build_exception_view_response(msg)
            return Response(json.dumps(exception_view_response),
                            mimetype='application/json',
                            status=200)

        if view_callback_id.startswith(SECRET_PREFIX + '#guess_view'):
            if game.time_left_to_guess < 0:
                msg = ('Your guess will not be taken into account '
                       'because the guessing deadline has passed!')
                exception_view_response = (
                    views.build_exception_view_response(msg))
                return Response(json.dumps(exception_view_response),
                                mimetype='application/json',
                                status=200)
            guess = views.collect_guess(view)
            game.guesses[user_id] = guess
            game.update_board('lower')
            return make_response('', 200)

        if view_callback_id.startswith(SECRET_PREFIX + '#vote_view'):
            if game.time_left_to_vote < 0:
                msg = ('Your vote will not be taken into account '
                       'because the voting deadline has passed!')
                exception_view_response = (
                    views.build_exception_view_response(msg))
                return Response(json.dumps(exception_view_response),
                                mimetype='application/json',
                                status=200)
            vote = views.collect_vote(view)
            game.votes[user_id] = vote
            game.update_board('lower')
            return make_response('', 200)

    if message_action_type == 'block_actions':
        action_block_id = message_action['actions'][0]['block_id']

        if not action_block_id.startswith(SECRET_PREFIX):
            return make_response('', 200)

        game_id = ids.slack_object_id_to_game_id(action_block_id)

        game = GAMES.get(game_id)

        if game is None:
            msg = 'This game is dead!'
            views.open_exception_view(slack_client, trigger_id, msg)
            return make_response('', 200)

        if action_block_id.startswith(SECRET_PREFIX + '#guess_button_block'):
            if user_id == game.organizer_id:
                msg = 'As the organizer of this game, you cannot guess!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id == 'Truth':
                msg = ("You cannot play bluffer because your slack user_id is "
                       "'Truth', which is a reserved word for the game.")
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id not in game.potential_guessers:
                msg = ('You cannot guess because when the set up of this '
                       'game started, you were not a member of this channel.')
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id in game.guessers:
                msg = 'You have already guessed!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            game.open_guess_view(trigger_id)
            return make_response('', 200)

        if action_block_id.startswith(SECRET_PREFIX + '#vote_button_block'):
            if user_id not in game.guessers:
                msg = 'Only guessers can vote!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id in game.voters:
                msg = 'You have already voted!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            game.open_vote_view(trigger_id, user_id)
            return make_response('', 200)


if __name__ == '__main__':
    thread_erase_dead_games = threading.Thread(target=erase_dead_games)
    thread_erase_dead_games.daemon = True
    thread_erase_dead_games.start()

    app.run(host='0.0.0.0', port=PORT)
