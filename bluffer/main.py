import os
import json
from flask import Flask, request, make_response
from slackclient import SlackClient
from bluffer.utils import get_bluffer_channel_id, get_modal, get_message

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)


add_me_to_bluffer_channel = get_modal(__file__, 'add_me_to_bluffer_channel.json')
initiate_command_from_bluffer_channel = get_modal(__file__, 'initiate_command_from_bluffer_channel.json')
a_game_is_already_running = get_modal(__file__, 'a_game_is_already_running.json')
game_setup = get_modal(__file__, 'game_setup.json')
board_blocks = get_message(__file__, 'board.json')

game = dict()


@app.route("/slack/command", methods=["POST"])
def command():

    bluffer_channel_id = get_bluffer_channel_id(slack_client)

    if not bluffer_channel_id:
        slack_client.api_call(
            "views.open",
            trigger_id=request.form['trigger_id'],
            view=add_me_to_bluffer_channel)

        return make_response("", 200)

    if request.form['channel_id'] != bluffer_channel_id:
        slack_client.api_call(
            "views.open",
            trigger_id=request.form['trigger_id'],
            view=initiate_command_from_bluffer_channel)

        return make_response("", 200)

    if game:
        slack_client.api_call(
            "views.open",
            trigger_id=request.form['trigger_id'],
            view=initiate_command_from_bluffer_channel)

        return make_response("", 200)

    game['organizer_id'] = request.form['user_id']

    slack_client.api_call(
        "views.open",
        trigger_id=request.form['trigger_id'],
        view=game_setup)

    return make_response("", 200)


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():

    message_action = json.loads(request.form["payload"])

    if message_action["type"] == "view_submission":
        view = message_action["view"]

        if view["callback_id"] == "game_setup":



    return make_response("", 200)


if __name__ == "__main__":
    app.run()
