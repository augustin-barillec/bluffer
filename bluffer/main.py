import os
import json
from flask import Flask, request, make_response
from slackclient import SlackClient
from bluffer.game import Game

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

games = dict()


@app.route("/slack/command", methods=["POST"])
def command():
    trigger_id = request.form['trigger_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    game = Game(trigger_id, channel_id, organizer_id, slack_client)
    games[organizer_id] = game
    game.ask_setup()
    return make_response("", 200)


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    message_action = json.loads(request.form["payload"])
    user_id = message_action['user']['id']
    if message_action["type"] == "view_submission":
        view = message_action["view"]
        if view["callback_id"] == "game_setup":
            organizer_id = user_id
            game = games[organizer_id]
            game.collect_setup(view)
            game.start()
    return make_response("", 200)


if __name__ == "__main__":
    app.run()
