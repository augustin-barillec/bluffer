import os
import json
import argparse
from flask import Flask, request, make_response
from slackclient import SlackClient
from bluffer.game import Game
from bluffer.utils import get_game, open_error_view

parser = argparse.ArgumentParser()
parser.add_argument('--is_test', type=bool, required=True)
args = parser.parse_args()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

games = dict()


@app.route("/slack/command", methods=["POST"])
def command():
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']
    if organizer_id in games:
        msg = ('You are the organizer of a game which is sill running. ' 
               'You can only have one game running at a time.')
        open_error_view(slack_client, trigger_id, msg)
        return make_response("", 200)
    game = Game(team_id, channel_id, organizer_id, trigger_id, slack_client,
                args.is_test)
    games[organizer_id] = game
    game.open_game_setup_view(trigger_id)
    return make_response("", 200)


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    message_action = json.loads(request.form["payload"])
    user_id = message_action['user']['id']

    if message_action["type"] == "block_actions":
        trigger_id = message_action['trigger_id']
        actions_block_id = message_action['actions'][0]['block_id']

        if not actions_block_id.startswith('bluffer'):
            return make_response("", 200)

        game = get_game(actions_block_id, games)
        if game is None:
            msg = 'This game is not running anymore !'
            open_error_view(slack_client, trigger_id, msg)
            return make_response("", 200)

        if actions_block_id.startswith("bluffer#guess_button"):
            if user_id == game.organizer_id:
                msg = 'As the organizer of this game, you cannot guess !'
                open_error_view(slack_client, trigger_id, msg)
                return make_response("", 200)
            previous_guess = None
            if user_id in game.guessers:
                previous_guess = game.guesses[user_id]
            game.open_guess_view(trigger_id, previous_guess)

        if actions_block_id.startswith("bluffer#vote_button"):
            if user_id not in game.guessers:
                msg = 'Only guessers can vote !'
                open_error_view(slack_client, trigger_id, msg)
                return make_response("", 200)
            previous_vote = None
            if user_id in game.voters:
                previous_vote = game.votes[user_id]
            game.open_vote_view(trigger_id, user_id, previous_vote)

    if message_action["type"] == "view_submission":
        view = message_action["view"]
        view_id = view["callback_id"]

        if not view_id.startswith('bluffer'):
            return make_response("", 200)

        game = get_game(view_id, games)

        if view_id.startswith("bluffer#game_setup_view"):
            game.collect_setup(view)
            game.start()

        if view_id.startswith("bluffer#guess_view"):
            game.add_or_update_guess(user_id, view)
            game.update_board()

        if view_id.startswith("bluffer#vote_view"):
            game.add_or_update_vote(user_id, view)
            game.update_board()

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
