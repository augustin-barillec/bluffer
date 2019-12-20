import time
import threading
import argparse
from flask import Flask, Response, request, make_response
from slackclient import SlackClient
from bluffer.game import Game
from bluffer.utils import *


parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
slack_client = SlackClient(token=SLACK_BOT_TOKEN)

APP_ID = os.environ['APP_ID']

app = Flask(__name__)

games = dict()


def erase_dead_games():
    while True:
        dead_game_ids = []
        for game_id in games:
            if games[game_id].is_over:
                dead_game_ids.append(game_id)
        for game_id in dead_game_ids:
            games[game_id].thread_update.join()
            del games[game_id]
        time.sleep(1)


thread_erase_dead_games = threading.Thread(target=erase_dead_games)
thread_erase_dead_games.daemon = True
thread_erase_dead_games.start()

app.run(host='0.0.0.0', port=5000)


@app.route('/slack/command', methods=['POST'])
def command():
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    if len(games) >= 100:
        msg = ('There are too many (more than 100) games '
               'running!')
        open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    app_conversations = slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']
    if channel_id not in [c['id'] for c in app_conversations]:
        msg = 'Please invite me first to this conversation!'
        open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    if organizer_id in [g.organizer_id for g in games if g.is_running]:
        msg = ('You are the organizer of a game which is sill running. '
               'You can only have one game running at a time.')
        open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    game_id = build_game_id(team_id, channel_id, organizer_id, trigger_id)
    open_game_setup_view(slack_client, trigger_id, game_id)

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

        if not view_callback_id.startswith(APP_ID):
            return make_response('', 200)

        game_id = slack_object_id_to_game_id(view_callback_id)

        if view_callback_id.startswith(APP_ID + '#game_setup_view'):
            question, truth, time_to_guess, time_to_vote = \
                collect_game_setup(view, args.debug)
            games[game_id] = Game(question, truth,
                                  time_to_guess, time_to_vote,
                                  game_id, slack_client)
            return make_response('', 200)

        game = games.get(game_id)
        if game is None:
            msg = 'This game is dead!'
            return Response(json.dumps(exception_view_response(msg)),
                            mimetype='application/json',
                            status=200)

        if view_callback_id.startswith(APP_ID + '#guess_view'):
            if game.time_left_to_guess < 0:
                msg = ('Your guess will not be taken into account '
                       'because the guessing deadline has passed!')
                return Response(json.dumps(exception_view_response(msg)),
                                mimetype='application/json',
                                status=200)
            game.add_guess(user_id, view)
            game.update()
            return make_response('', 200)

        if view_callback_id.startswith(APP_ID + '#vote_view'):
            if game.time_left_to_vote < 0:
                msg = ('Your vote will not be taken into account '
                       'because the voting deadline has passed!')
                return Response(json.dumps(exception_view_response(msg)),
                                mimetype='application/json',
                                status=200)
            game.add_vote(user_id, view)
            game.update()
            return make_response('', 200)

    if message_action_type == 'block_actions':
        action_block_id = message_action['actions'][0]['block_id']

        if not action_block_id.startswith(APP_ID):
            return make_response('', 200)

        game_id = slack_object_id_to_game_id(action_block_id)

        game = games.get(game_id)
        if game is None:
            msg = 'This game is dead!'
            return Response(json.dumps(exception_view_response(msg)),
                            mimetype='application/json',
                            status=200)

        if action_block_id.startswith(APP_ID + '#guess_button_block'):
            if user_id == game.organizer_id:
                msg = 'As the organizer of this game, you cannot guess!'
                open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id == 'Truth':
                msg = ("You cannot play bluffer because your slack user_id is "
                       "'Truth', which is a reserved word for the game.")
                open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id not in game.potential_guessers:
                msg = ('You cannot guess because when the set up of this '
                       'game started, you were not a member of this channel.')
                open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id in game.guessers:
                msg = 'You have already guessed!'
                open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            game.open_guess_view(trigger_id)
            return make_response('', 200)

        if action_block_id.startswith(APP_ID + '#vote_button_block'):
            if user_id not in game.guessers:
                msg = 'Only guessers can vote!'
                open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if user_id in game.voters:
                msg = 'You have already voted!'
                open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            game.open_vote_view(trigger_id, user_id)
            return make_response('', 200)
