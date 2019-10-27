import json
import os
from flask import Flask, request, make_response
from slackclient import SlackClient

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

BLUFFER_CHANNEL = 'GNE9G4GBT'

with open('bluffer/jsons/messages/board.json') as f:
    blocks = json.load(f)['blocks']


@app.route("/slack/command", methods=["POST"])
def launch_game():
    print(request.form['channel_id'])

    post_message = slack_client.api_call(
        "chat.postMessage",
        channel=request.form['channel_id'],
        text="",
        blocks=blocks)

    print(post_message)

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
