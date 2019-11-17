import os
import json
import argparse
from flask import Flask, request, make_response
from slackclient import SlackClient
from bluffer.game import Game
from bluffer.utils import get_game

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
        raise RuntimeError(
            """
            A game organized by {} is alreay running.
            A user can only have one game running at a
            time.
            """.format(organizer_id))
    game = Game(team_id, channel_id, organizer_id, trigger_id, slack_client,
                args.is_test)
    games[organizer_id] = game
    game.open_game_setup_view(trigger_id)
    return make_response("", 200)


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    message_action = json.loads(request.form["payload"])
    user_id = message_action['user']['id']

    if message_action["type"] == "view_submission":
        view = message_action["view"]
        view_id = view["callback_id"]

        if view_id.startswith("bluffer#game_setup_view"):
            game = get_game(view_id, games)
            game.collect_setup(view)
            game.start()

        if view_id.startswith("bluffer#guess_view"):
            game = get_game(view_id, games)
            game.add_or_update_guess(user_id, view)
            if user_id not in game.guessers:
                game.guessers.append(user_id)
            game.update_board()

        if view_id.startswith("bluffer#vote_view"):
            game = get_game(view_id, games)
            game.add_or_update_vote(user_id, view)
            if user_id not in game.voters:
                game.voters.append(user_id)
            game.update_board()

    if message_action["type"] == "block_actions":
        trigger_id = message_action['trigger_id']
        actions_block_id = message_action['actions'][0]['block_id']

        if actions_block_id.startswith("bluffer#guess_button"):
            game = get_game(actions_block_id, games)
            if user_id != game.organizer_id:
                previous_guess = None
                if user_id in game.guesses:
                    previous_guess = game.guesses[user_id]
                game.open_guess_view(trigger_id, previous_guess)

        if actions_block_id.startswith("bluffer#vote_button"):
            game = get_game(actions_block_id, games)
            if user_id in game.guessers:
                previous_vote = None
                if user_id in game.votes:
                    previous_vote = game.votes[user_id]
                game.open_vote_view(trigger_id, user_id, previous_vote)

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
