import time
import threading
import os
import json
import argparse
from flask import Flask, Response, request, make_response
from slackclient import SlackClient
from bluffer.game import Game
from bluffer.utils import build_game_id, get_game, open_exception_view, \
    exception_view_response

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
slack_client = SlackClient(token=SLACK_BOT_TOKEN)
app = Flask(__name__)

games = dict()


@app.route('/slack/command', methods=['POST'])
def command():
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    app_conversations = slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']
    if channel_id not in [c['id'] for c in app_conversations]:
        msg = 'Please invite me first to this conversation!'
        open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    organizer_id_has_game_running = False
    for game_id in games:
        game = games[game_id]
        if organizer_id == game.organizer_id and game.is_running:
            organizer_id_has_game_running = True
    if organizer_id_has_game_running:
        msg = ('You are the organizer of a game which is sill running. '
               'You can only have one game running at a time.')
        open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    game = Game(team_id, channel_id, organizer_id, trigger_id,
                slack_client, args.debug)
    game_id = build_game_id(team_id, channel_id, organizer_id, trigger_id)
    games[game_id] = game
    game.open_game_setup_view(trigger_id)
    return make_response('', 200)


@app.route('/slack/message_actions', methods=['POST'])
def message_actions():
    message_action = json.loads(request.form['payload'])
    user_id = message_action['user']['id']
    trigger_id = message_action['trigger_id']

    if message_action['type'] == 'block_actions':
        action_block_id = message_action['actions'][0]['block_id']

        if not action_block_id.startswith('bluffer'):
            return make_response('', 200)

        game = get_game(action_block_id, games)
        if game is None:
            msg = 'This game is dead!'
            open_exception_view(slack_client, trigger_id, msg)
            return make_response('', 200)

        if action_block_id.startswith('bluffer#guess_button_block'):
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

        if action_block_id.startswith('bluffer#vote_button_block'):
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

    if message_action['type'] == 'view_submission':
        view = message_action['view']
        view_callback_id = view['callback_id']

        if not view_callback_id.startswith('bluffer'):
            return make_response('', 200)

        game = get_game(view_callback_id, games)
        if game is None:
            msg = 'This game is dead!'
            return Response(json.dumps(exception_view_response(msg)),
                            mimetype='application/json',
                            status=200)

        if view_callback_id.startswith('bluffer#game_setup_view'):
            game.collect_setup(view)
            game.start()
            return make_response('', 200)

        if view_callback_id.startswith('bluffer#guess_view'):
            if game.stage != 'guess_stage':
                msg = ('Your guess will not be taken into account '
                       'because the guessing deadline has passed!')
                return Response(json.dumps(exception_view_response(msg)),
                                mimetype='application/json',
                                status=200)
            game.add_guess(user_id, view)
            game.update()
            return make_response('', 200)

        if view_callback_id.startswith('bluffer#vote_view'):
            if game.stage != 'vote_stage':
                msg = ('Your vote will not be taken into account '
                       'because the voting deadline has passed!')
                return Response(json.dumps(exception_view_response(msg)),
                                mimetype='application/json',
                                status=200)
            game.add_vote(user_id, view)
            game.update()
            return make_response('', 200)

    return make_response('', 200)


if __name__ == '__main__':

    def erase_dead_games():
        while True:
            dead_game_ids = []
            for game_id in games:
                if games[game_id].is_over:
                    dead_game_ids.append(game_id)
            for game_id in dead_game_ids:
                del games[game_id]
            time.sleep(1)
    thread_erase_dead_games = threading.Thread(target=erase_dead_games)
    thread_erase_dead_games.daemon = True
    thread_erase_dead_games.start()

    app.run(host='0.0.0.0', port=5000)
