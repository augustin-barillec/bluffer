import json
import os
from flask import Flask, request, make_response
from slackclient import SlackClient

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

BLUFFER_CHANNEL = 'GNE9G4GBT'

with open('tata.json') as f:
    view = json.load(f)


@app.route("/slack/command", methods=["POST"])
def launch_game():
    print(request.form)

    toto = slack_client.api_call(
            "views.open",
            trigger_id=request.form['trigger_id'],
            view=view)

    print(toto)

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
