import json
import os
from flask import Flask, request, make_response
from slackclient import SlackClient

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

BLUFFER_CHANNEL = 'GNE9G4GBT'

# with open('bluffer/jsons/modals/game_setup.json') as f:
#     view = json.load(f)

view = {'type': 'modal', 'callback_id': 'bluffer#vote_view#TLEN0RAUD#CLGRZ3KB8#ULGRZ3154#837559908180.694748860965.858c55326d366e75c61d8889b229d510', 'title': {'type': 'plain_text', 'text': 'bluffer', 'emoji': True}, 'submit': {'type': 'plain_text', 'text': 'Submit', 'emoji': True}, 'close': {'type': 'plain_text', 'text': 'Cancel', 'emoji': True}, 'blocks': [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'Your guess is: 2) c'}}, {'type': 'input', 'block_id': 'vote', 'label': {'type': 'plain_text', 'text': 'Your vote', 'emoji': True}, 'element': {'type': 'static_select', 'action_id': 'vote', 'placeholder': {'type': 'plain_text', 'text': 'Select an item', 'emoji': True}, 'options': [{'text': {'type': 'plain_text', 'text': '1) b', 'emoji': True}, 'value': '1'}]}}]}

@app.route("/slack/command", methods=["POST"])
def launch_game():
    print(request.form)

    toto = slack_client.api_call(
            "views.open",
            trigger_id=request.form['trigger_id'],
            view=view)

    # print(toto)

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
